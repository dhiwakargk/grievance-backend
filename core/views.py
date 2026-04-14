from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Count
from django.contrib.auth.hashers import make_password
from .models import User, Department, Grievance, StatusLog
from .serializers import (
    UserSerializer, DepartmentSerializer, GrievanceSerializer, 
    GrievanceCreateSerializer, StatusLogSerializer
)
from .utils.ai_handler import AIHandler
from .utils.ocr_handler import OCRHandler

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    if request.method == 'POST':
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'POST'])
def department_list(request):
    if request.method == 'GET':
        if not request.user.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        departments = Department.objects.all()
        serializer = DepartmentSerializer(departments, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        if not request.user.is_staff:
             return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = DepartmentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
def department_detail(request, pk):
    if not request.user.is_authenticated:
        return Response(status=status.HTTP_401_UNAUTHORIZED)
    
    department = get_object_or_404(Department, pk=pk)

    if request.method == 'GET':
        serializer = DepartmentSerializer(department)
        return Response(serializer.data)

    elif request.method == 'PUT':
        if not request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = DepartmentSerializer(department, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        if not request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        department.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def grievance_list_create(request):
    if request.method == 'GET':
        user = request.user
        mode = request.query_params.get('mode')
        
        if user.role == 'citizen':
            grievances = Grievance.objects.filter(user=user)
        elif user.role == 'official':
            if mode == 'all':
                grievances = Grievance.objects.all()
            else:
                grievances = Grievance.objects.filter(assigned_user=user)
        elif user.role == 'admin':
            grievances = Grievance.objects.all()
        else:
            grievances = Grievance.objects.none()
            
        serializer = GrievanceSerializer(grievances, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = GrievanceCreateSerializer(data=request.data)
        if serializer.is_valid():
            # Handle Image & AI
            image = request.FILES.get('image')
            extracted_text = ""
            if image:
                extracted_text = OCRHandler.extract_text(image)
                print(f"DEBUG: OCR Raw Output: '{extracted_text}'")
            
            title = serializer.validated_data.get('title', 'Untitled Grievance').strip()
            description = serializer.validated_data.get('description', '').strip()
            latitude = serializer.validated_data.get('latitude')
            longitude = serializer.validated_data.get('longitude')
            
            if not title or title.lower() in ["nil", "none", "null"]:
                title = "Untitled Grievance"
            
            # Populate description from OCR if it's an image-only submission
            if not description and extracted_text:
                description = extracted_text[:1000] # Use extracted text as description
                print(f"DEBUG: Populated description from OCR: '{description}'")

            print(f"DEBUG: Submission - Title: '{title}', Description: '{description}'")
            
            full_text = f"Title: {title}\nDescription: {description}\nExtracted from Image: {extracted_text}"
            
            
            # AI Analysis
            ai = AIHandler()
            
            # Translate to English if needed
            translated_title = ai.translate_to_english(title)
            translated_description = ai.translate_to_english(description)
            
            # Safety check after translation
            if not translated_title or translated_title.lower() in ["nil", "none", "null"]:
                translated_title = title if title and title.lower() not in ["nil", "none", "null"] else "Untitled Grievance"
            
            if translated_description.lower() in ["nil", "none", "null"]:
                translated_description = ""
            
            print(f"DEBUG: Translated - Title: '{translated_title}', Description: '{translated_description}'")
            
            # Combine everything for analysis
            # Ensure extracted_text is included even if others are empty
            full_text = f"Title: {translated_title}\nDescription: {translated_description}\nExtracted from Image: {extracted_text}"
            print(f"DEBUG: Full Text for AI: '{full_text}'")
            
            all_depts = list(Department.objects.values_list('name', flat=True))
            if not all_depts:
                all_depts = ["Roads", "Water", "Electricity", "Police", "Health", "Sanitation"]
            
            analysis = ai.analyze_grievance(full_text, valid_departments=all_depts)
            print(f"DEBUG: AI Analysis Result: {analysis}")
            
            # Find Dept
            suggested_dept_name = analysis['department']
            dept = None
            
            # Try exact match first
            dept = Department.objects.filter(name__iexact=suggested_dept_name).first()
            if dept:
                print(f"DEBUG: Found exact match: {dept.name}")
            
            # If not found, try containing match on the first word
            if not dept:
                first_word = suggested_dept_name.split(' ')[0]
                dept = Department.objects.filter(name__icontains=first_word).first()
                if dept:
                    print(f"DEBUG: Found partial match: {dept.name}")
            
            # Fallback to "General"
            if not dept:
                dept = Department.objects.filter(name__iexact="General").first()
                if dept:
                     print(f"DEBUG: Fallback to General")
                else:
                     print(f"DEBUG: General department not found!")
            
            # Final Fallback check before creation
            final_title = translated_title if translated_title and translated_title.lower() not in ["nil", "none", "null"] else title
            
            # Use AI Suggested title if the current title is generic
            if final_title == "Untitled Grievance" and analysis.get('suggested_title'):
                final_title = analysis['suggested_title']
                print(f"DEBUG: Using AI suggested title: '{final_title}'")

            final_description = translated_description if translated_description and translated_description.lower() not in ["nil", "none", "null"] else description

            # Load-balancing Auto Assignment
            assigned_user = None
            if dept:
                from django.db.models import Count, Q
                officials = User.objects.filter(role='official', department=dept)
                if officials.exists():
                    officials = officials.annotate(
                        active_count=Count('assigned_grievances', filter=Q(
                            assigned_grievances__status__in=['submitted', 'viewed', 'in_progress']
                        ))
                    ).order_by('active_count')
                    assigned_user = officials.first()
                    print(f"DEBUG: Assigned to {assigned_user.username} with {assigned_user.active_count} active grievances")

            grievance = Grievance.objects.create(
                user=request.user,
                title=final_title,
                description=final_description,
                image=image,
                latitude=latitude,
                longitude=longitude,
                extracted_text=extracted_text,
                ai_summary=analysis['summary'],
                urgency=analysis['urgency'],
                department=dept,
                assigned_user=assigned_user,
                status='submitted'
            )
            
            # Log
            StatusLog.objects.create(grievance=grievance, status='submitted')
            
            return Response(GrievanceSerializer(grievance).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def grievance_detail(request, pk):
    # We need to filter based on permission logic similar to list
    # But get_object_or_404 just gets it. We should check obj permissions.
    # For MVP, let's just get it and check ownership if citizen.
    
    grievance = get_object_or_404(Grievance, pk=pk)
    user = request.user

    # Permission check
    if user.role == 'citizen' and grievance.user != user:
        return Response(status=status.HTTP_403_FORBIDDEN)
    if user.role == 'official' and request.method != 'GET' and grievance.department != user.department:
         return Response(status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        serializer = GrievanceSerializer(grievance)
        return Response(serializer.data)

    elif request.method == 'PUT':
        # Full update
        serializer = GrievanceSerializer(grievance, data=request.data, partial=True) # Allow partial just in case
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    elif request.method == 'DELETE':
         if user.role == 'citizen':
             if grievance.user != user:
                 return Response(status=status.HTTP_403_FORBIDDEN)
             # Citizen can delete their own grievance
             grievance.delete()
             return Response(status=status.HTTP_204_NO_CONTENT)
         
         elif user.role in ['admin', 'official']:
             # Admin/Official can only delete if resolved
             if grievance.status == 'resolved':
                 grievance.delete()
                 return Response(status=status.HTTP_204_NO_CONTENT)
             return Response(
                 {"error": "Officials/Admins can only delete resolved grievances."}, 
                 status=status.HTTP_403_FORBIDDEN
             )
             
         return Response(status=status.HTTP_403_FORBIDDEN)

from django.core.mail import send_mail
from django.conf import settings

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_grievance_status(request, pk):
    grievance = get_object_or_404(Grievance, pk=pk)
    user = request.user
    
    # Check official/admin permission
    if user.role == 'citizen':
        return Response(status=status.HTTP_403_FORBIDDEN)
    if user.role == 'official' and grievance.department != user.department:
        return Response(status=status.HTTP_403_FORBIDDEN)
        
    new_status = request.data.get('status')
    remarks = request.data.get('remarks', '')
    
    if new_status:
        grievance.status = new_status
        grievance.remarks = remarks
        grievance.save()
        StatusLog.objects.create(grievance=grievance, status=new_status, changed_by=user, remarks=remarks)
        
        # Send Email Notification
        try:
            subject = f"Update on your grievance: {grievance.title}"
            message = f"Hello {grievance.user.username},\n\nYour grievance (ID: {grievance.id}) has been updated.\n\nNew Status: {grievance.status}\nAuthority Remarks: {grievance.remarks}\n\nThank you for using the Grievance Portal."
            recipient_list = [grievance.user.email]
            
            if grievance.user.email:
                send_mail(
                    subject,
                    message,
                    settings.EMAIL_HOST_USER,
                    recipient_list,
                    fail_silently=False,
                )
                print(f"DEBUG: Email sent to {grievance.user.email}")
            else:
                print(f"DEBUG: User {grievance.user.username} has no email address.")
        except Exception as e:
            print(f"DEBUG: Failed to send email: {e}")

        return Response({'status': 'updated'})
    return Response({'error': 'status required'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    user = request.user
    data = {}
    
    qs = Grievance.objects.all()
    if user.role == 'citizen':
        qs = qs.filter(user=user)
    elif user.role == 'official':
        qs = qs.filter(assigned_user=user)
        
    data['total'] = qs.count()
    data['submitted'] = qs.filter(status='submitted').count()
    data['in_progress'] = qs.filter(status='in_progress').count()
    data['resolved'] = qs.filter(status='resolved').count()
    data['rejected'] = qs.filter(status='rejected').count()
    
    return Response(data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_info(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)

@api_view(['GET', 'POST', 'DELETE'])
@permission_classes([IsAdminUser])
def manage_officials(request):
    if request.method == 'GET':
        officials = User.objects.filter(role='official')
        serializer = UserSerializer(officials, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        username = request.data.get('username')
        password = request.data.get('password')
        department_id = request.data.get('department')
        
        if not username or not password or not department_id:
             return Response({"error": "Username, password and department are required"}, status=status.HTTP_400_BAD_REQUEST)
             
        if User.objects.filter(username=username).exists():
             return Response({"error": "Username already exists"}, status=status.HTTP_400_BAD_REQUEST)
             
        department = get_object_or_404(Department, pk=department_id)
        
        user = User.objects.create(
            username=username,
            password=make_password(password),
            role='official',
            department=department
        )
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

    elif request.method == 'DELETE':
        user_id = request.data.get('user_id') or request.query_params.get('user_id')
        if not user_id:
             return Response({"error": "user_id required"}, status=status.HTTP_400_BAD_REQUEST)
        
        user = get_object_or_404(User, pk=user_id)
        if user.role != 'official':
             return Response({"error": "Can only delete officials"}, status=status.HTTP_400_BAD_REQUEST)
             
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
