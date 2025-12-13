from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import LoginForm


def landing(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'authentication/landing.html')

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}!')
                return redirect('dashboard')
    else:
        form = LoginForm()
    return render(request, 'authentication/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('login')

@login_required
def dashboard_view(request):
    if request.user.is_student():
        return redirect('student_dashboard')
    elif request.user.is_teacher():
        return redirect('teacher_dashboard')
    return render(request, 'authentication/dashboard.html')
