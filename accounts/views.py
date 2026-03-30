from django.contrib.auth import authenticate, login
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status


@api_view(["POST"])
def login_view(request):
    username = request.data.get("username")
    password = request.data.get("password")

    user = authenticate(request, username=username, password=password)

    if user is not None:
        login(request, user)
        return Response({"detail": "OK"})
    else:
        return Response(
            {"detail": "Invalid credentials"},
            status=status.HTTP_400_BAD_REQUEST
        )
        
@api_view(["GET"])
def me_view(request):
    if request.user.is_authenticated:
        return Response({
            "id": request.user.id,
            "username": request.user.username,
        })
    return Response(
        {"detail": "Unauthorized"},
        status=status.HTTP_401_UNAUTHORIZED
    )