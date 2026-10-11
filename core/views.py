from django.contrib.auth.hashers import make_password, check_password
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from .models import UserInfos, LoginUsers, CompanyDetails, LocationInfos
from django.contrib.auth.hashers import make_password, check_password

def register_view(request):

    if request.method == "POST":
        full_name = request.POST.get("full_name")
        email = request.POST.get("email")
        password = request.POST.get("password")


        if not full_name or not email or not password:
            messages.error(request, "All fields are required")

            return redirect("register")


        if UserInfos.objects.filter(user_email=email).exists():
            messages.error(request, "Email already registered")

            return redirect("register")

        # Always create SU user
        last_su_user = UserInfos.objects.filter(user_id__startswith="SU").order_by('-id').first()
        last_num = int(last_su_user.user_id[2:]) if last_su_user else 0
        new_user_id = f"SU{last_num + 1:010d}"  # 12 digits: SU + 10 digits

        try:

            hashed_password = make_password(password)  # hash the password

            new_user = UserInfos.objects.create(
                user_id=new_user_id,
                login_user_id=None,
                title=None,
                user_name=full_name,
                user_email=email,
                user_phone=None,
                gender=None,
                loc_id=None,
                user_role=1,  # Superadmin role id
                tran_user_type=None,
                tran_method="payment",
                tran_with_id=0,
                dob=None,
                nationality=None,
                religion=None,
                nid=None,
                passport=None,
                driving_lisence=None,
                address=None,
                corporate_id=None,
                password=hashed_password,  # store hashed password
                image=None,
                store=None,

                company_id=None,
                status=1,
                added_at=timezone.now(),
                updated_at=None
            )
            new_user.save()
            messages.success(request, f"Registration successful! User ID: {new_user_id}")

            return redirect("login")
        except Exception as e:
            messages.error(request, f"Registration failed: {str(e)}")

            return redirect("register")


    return render(request, "auth/register.html")


def login_view(request):

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        try:

            user_obj = UserInfos.objects.get(user_email=email)
        except UserInfos.DoesNotExist:
            messages.error(request, "Invalid email or password")

            return redirect("login")


        if check_password(password, user_obj.password):  # verify hashed password

            request.session['user_id'] = user_obj.user_id

            request.session['user_name'] = user_obj.user_name

            request.session['user_role'] = user_obj.user_role

            return redirect("dashboard")

        else:
            messages.error(request, "Invalid email or password")

            return redirect("login")


    return render(request, "auth/login.html")


def _password_matches(raw_password, db_password):

    if not db_password:

        return False
    if str(db_password).startswith('pbkdf2_'):

        return check_password(raw_password, db_password)
    return raw_password == db_password

def _media_url(file_name):

    if not file_name:

        return ""
    if str(file_name).startswith(('/media/', 'http://', 'https://')):

        return file_name
    return f"/media/{file_name}"

def _set_login_session(request, user_obj):

    login_user = LoginUsers.objects.filter(user_id=user_obj.login_user_id or user_obj.user_id).first() if hasattr(user_obj, "login_user_id") else user_obj
    company_id = getattr(user_obj, "company_id", None) or (login_user.company_id if login_user else None)
    user_info = UserInfos.objects.filter(user_id=getattr(user_obj, "user_id", None)).first() or UserInfos.objects.filter(login_user_id=getattr(user_obj, "user_id", None)).first()
    location_id = getattr(user_obj, "loc_id", None) or (user_info.loc_id if user_info else None)
    if not location_id and getattr(user_obj, "user_name", None):

        user_info = UserInfos.objects.filter(user_name=user_obj.user_name, loc_id__isnull=False).order_by("-id").first()
        location_id = user_info.loc_id if user_info else None
    location = LocationInfos.objects.filter(id=location_id, status=1).first() if location_id else None
    company = CompanyDetails.objects.filter(company_id=company_id).first() if company_id else None
    request.session['user_id'] = user_obj.user_id
    request.session['user_name'] = user_obj.user_name
    request.session['user_role'] = getattr(user_obj, "user_role_id", None) or getattr(user_obj, "user_role", None)
    request.session['loc_id'] = location.id if location else ""
    request.session['location_name'] = location.division if location else ""
    request.session['company_name'] = company.company_name if company else "TEAM SOLUTIONS BANGLADESH"
    request.session['company_logo'] = _media_url(company.logo) if company and company.logo else ""

def _find_login_user(email, password):

    user_info_candidates = list(UserInfos.objects.filter(user_email=email).order_by('-status', '-id'))
    login_user_candidates = list(LoginUsers.objects.filter(user_email=email).order_by('-status', '-id'))
    for candidate in user_info_candidates + login_user_candidates:

        if _password_matches(password, candidate.password):

            return candidate
    return None


def login_view(request):

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")


        user_obj = _find_login_user(email, password)
        if not user_obj:
            messages.error(request, "Invalid email or password")

            return redirect("login")

        db_pass = user_obj.password


        if db_pass and not str(db_pass).startswith('pbkdf2_'):

            user_obj.password = make_password(password)
            user_obj.save()

        _set_login_session(request, user_obj)
        return redirect("dashboard")


    return render(request, "auth/login.html")



def dashboard(request):
    # check session manually

    if not request.session.get('user_id'):

        return redirect('login')


    return render(request, 'dashboard/dashboard.html')


def logout_view(request):

    request.session.flush()  # clear all session data

    return redirect('login')
