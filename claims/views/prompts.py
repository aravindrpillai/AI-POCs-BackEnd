from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from claims.models import ClaimPrompts


class ClaimPromptsAPIView(APIView):
    def get_object(self, uid):
        try:
            return ClaimPrompts.objects.get(uid=uid)
        except ClaimPrompts.DoesNotExist:
            return None

    def format_data(self, obj):
        return {
            "uid": str(obj.uid),
            "active": obj.active,
            "name": obj.name,
            "prompt": obj.prompt,
            "updated_on": obj.updated_on,
            "created_on": obj.created_on,
        }

    def get(self, request, uid=None):
        if uid:
            obj = self.get_object(uid)
            if not obj:
                return Response(
                    {"status": False, "message": "Record not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            return Response(
                {"status": True, "data": self.format_data(obj)},
                status=status.HTTP_200_OK
            )

        queryset = ClaimPrompts.objects.all().order_by("-created_on")
        data = [self.format_data(obj) for obj in queryset]

        return Response(
            {"status": True, "data": data},
            status=status.HTTP_200_OK
        )

    def post(self, request):
        name = request.data.get("name")
        prompt = request.data.get("prompt")

        if not name:
            return Response(
                {"status": False, "message": "name is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not prompt:
            return Response(
                {"status": False, "message": "prompt is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        obj = ClaimPrompts.objects.create(
            name=name,
            prompt=prompt,
            active=0,
            updated_on=timezone.now()
        )

        return Response(
            {
                "status": True,
                "message": "Record created successfully",
                "data": self.format_data(obj)
            },
            status=status.HTTP_201_CREATED
        )

    def put(self, request, uid=None):
        if not uid:
            return Response(
                {"status": False, "message": "uid is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        obj = self.get_object(uid)
        if not obj:
            return Response(
                {"status": False, "message": "Record not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        name = request.data.get("name", None)
        prompt = request.data.get("prompt", None)
        active = request.data.get("active", None)

        if name is not None:
            obj.name = name

        if prompt is not None:
            obj.prompt = prompt

        if active is not None:
            try:
                active = int(active)
            except (ValueError, TypeError):
                return Response(
                    {"status": False, "message": "active must be 0 or 1"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if active not in [0, 1]:
                return Response(
                    {"status": False, "message": "active must be 0 or 1"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if active == 1:
                ClaimPrompts.objects.exclude(uid=obj.uid).update(active=0)

            obj.active = active

        obj.updated_on = timezone.now()
        obj.save()

        return Response(
            {
                "status": True,
                "message": "Record updated successfully",
                "data": self.format_data(obj)
            },
            status=status.HTTP_200_OK
        )
    
    
    def delete(self, request, uid=None):
        if not uid:
            return Response(
                {"status": False, "message": "uid is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        obj = self.get_object(uid)
        if not obj:
            return Response(
                {"status": False, "message": "Record not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # 🚫 Prevent deleting active record
        if obj.active == 1:
            return Response(
                {"status": False, "message": "Active record cannot be deleted"},
                status=status.HTTP_400_BAD_REQUEST
            )

        obj.delete()

        return Response(
            {"status": True, "message": "Record deleted successfully"},
            status=status.HTTP_200_OK
        )