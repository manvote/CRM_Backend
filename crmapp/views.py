from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.tokens import RefreshToken
import json

@csrf_exempt
def login_view(request):

    if request.method == "POST":
        data = json.loads(request.body)

        user = authenticate(
            username=data.get("username"),
            password=data.get("password")
        )

        if not user:
            return JsonResponse(
                {"error": "Invalid credentials"},
                status=400
            )

        refresh = RefreshToken.for_user(user)

        return JsonResponse({
            "message": "Login success",
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh)
        })

    return JsonResponse(
        {"message": "Only POST method allowed"},
        status=405
    )
