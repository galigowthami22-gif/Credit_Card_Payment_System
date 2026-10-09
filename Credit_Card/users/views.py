from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST
from .roles import ROLE_MANAGER, ROLE_USER, assign_role
from .tokens import create_access_token


@login_required
@require_GET
@never_cache
def token_view(request):
    return JsonResponse({
        'access_token': create_access_token(request.user.pk),
        'token_type': 'bearer',
    })


def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password')
        role = request.POST.get('role', ROLE_USER).strip()

        if role not in (ROLE_USER, ROLE_MANAGER):
            messages.error(request, 'Select a valid role.')
            return redirect('register')

        if not username or len(username) > 150 or not email or len(email) > 254 or not password:
            messages.error(request, 'Enter a valid username, email address, and password.')
            return redirect('register')
        try:
            validate_email(email)
            validate_password(password, User(username=username, email=email))
        except ValidationError as error:
            for message in error.messages:
                messages.error(request, message)
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return redirect('register')

        user = User.objects.create_user(username=username, email=email, password=password)
        assign_role(user, role)
        login(request, user)
        return redirect('dashboard')

    return render(
        request,
        'users/register.html',
        {'role_choices': ((ROLE_USER, 'User'), (ROLE_MANAGER, 'Manager'))},
    )


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password')
        if not username or not password:
            messages.error(request, 'Enter your username and password.')
            return redirect('login')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid credentials')
            return redirect('login')

    return render(request, 'users/login.html')


@require_POST
def logout_view(request):
    logout(request)
    return redirect('login')
