import traceback
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from files.models.file_conversation import FileConversation
from files.models.conversation import Conversation
from files.query import handle_query


class ChatAPIView(APIView):

    def get(self, request):
        """
        GET /ai/files/chat/?conv_id=<uuid>
        Load full chat history.
        """
        conv_id = request.query_params.get('conv_id')
        if not conv_id:
            return Response({'error': 'conv_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            file_conversation = FileConversation.objects.get(conv_id=conv_id)
        except FileConversation.DoesNotExist:
            print(traceback.print_exc())
            return Response({'error': 'Conversation not found.'}, status=status.HTTP_404_NOT_FOUND)

        messages = Conversation.objects.filter(file_conversation=file_conversation).values(
            'id', 'role', 'content', 'references', 'created_at'
        )

        return Response({'conv_id': str(conv_id), 'messages': list(messages)})

    def post(self, request):
        """
        POST /ai/files/chat/
        Body: { "conv_id": "<uuid>", "message": "..." }
        """
        conv_id = request.data.get('conv_id')
        message = request.data.get('message', '').strip()

        if not conv_id:
            return Response({'error': 'conv_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not message:
            return Response({'error': 'message is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = handle_query(conv_id, message)
        except FileConversation.DoesNotExist:
            return Response({'error': 'Conversation not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(traceback.print_exc())    
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(result, status=status.HTTP_200_OK)