import os, traceback
import mimetypes
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.db import transaction
from files.models.file_conversation import FileConversation
from files.models.files import File
from files.vectorise import vectorise_file


class FileAPIView(APIView):

    def get(self, request):
        conv_id = request.query_params.get('conv_id')
        if not conv_id:
            return Response({'error': 'conv_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            file_conversation = FileConversation.objects.get(conv_id=conv_id)
        except FileConversation.DoesNotExist:
            return Response({'error': 'Conversation not found.'}, status=status.HTTP_404_NOT_FOUND)

        files = File.objects.filter(file_conversation=file_conversation).values(
            'id', 'file_name', 'mime_type', 'uploaded_at'
        )

        return Response({
            'conv_id': conv_id,
            'files': list(files)
        }, status=status.HTTP_200_OK)

    def post(self, request):
        files = request.FILES.getlist('files')

        if not files:
            return Response({'error': 'No files provided.'}, status=status.HTTP_400_BAD_REQUEST)

        saved_paths = []

        try:
            with transaction.atomic():
                file_conversation = FileConversation.objects.create()

                for file in files:
                    ext = os.path.splitext(file.name)[1].lower()
                    mime_type, _ = mimetypes.guess_type(file.name)

                    # Create DB record first to get the UUID
                    file_record = File.objects.create(
                        file_conversation=file_conversation,
                        file_name=file.name,
                        mime_type=mime_type or '',
                        extension=ext,
                    )

                    # Save file as <file_id><ext>
                    dest_dir = os.path.join(settings.STATIC_ROOT, "uploads", "files")
                    os.makedirs(dest_dir, exist_ok=True)
                    dest_path = os.path.join(dest_dir, f'{file_record.id}{ext}')

                    with open(dest_path, 'wb') as f:
                        for chunk in file.chunks():
                            f.write(chunk)
                    saved_paths.append(dest_path)

                    vectorise_file(file_record)

        except Exception as e:
            print(traceback.print_exc())
            for path in saved_paths:
                if os.path.exists(path):
                    os.remove(path)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'conv_id': str(file_conversation.conv_id),
            'uploaded': [os.path.basename(p) for p in saved_paths]
        }, status=status.HTTP_201_CREATED)