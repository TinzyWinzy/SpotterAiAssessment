"""Auth endpoints: register, login, logout, me."""
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .serializers import RegisterSerializer, LoginSerializer, UserSerializer


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"ok": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )
    result = serializer.save()
    return Response(
        {
            "ok": True,
            "token": result["token"].key,
            "user": UserSerializer(result["user"]).data,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"ok": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )
    user = authenticate(
        username=serializer.validated_data["username"],
        password=serializer.validated_data["password"],
    )
    if user is None:
        return Response(
            {"ok": False, "error": "invalid credentials"},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    token, _ = Token.objects.get_or_create(user=user)
    return Response({
        "ok": True,
        "token": token.key,
        "user": UserSerializer(user).data,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    Token.objects.filter(user=request.user).delete()
    return Response({"ok": True})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return Response({
        "ok": True,
        "user": UserSerializer(request.user).data,
    })
