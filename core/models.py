from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('citizen', 'Citizen'),
        ('official', 'Official'),
        ('admin', 'Admin'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='citizen')
    department = models.ForeignKey('Department', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.username

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Grievance(models.Model):
    URGENCY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    )
    STATUS_CHOICES = (
        ('submitted', 'Submitted'),
        ('viewed', 'Viewed'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('rejected', 'Rejected'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='grievances')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    assigned_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_grievances')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='grievances/', blank=True, null=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    extracted_text = models.TextField(blank=True)
    ai_summary = models.TextField(blank=True)
    urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES, default='low')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    remarks = models.TextField(blank=True)

    def __str__(self):
        return f"{self.title} - {self.status}"
    
    def save(self, *args, **kwargs):
        # Auto-track status changes could go here, or in signals.
        # For simplicity in MVP, we might handle it in the view or signal.
        super().save(*args, **kwargs)

class StatusLog(models.Model):
    grievance = models.ForeignKey(Grievance, on_delete=models.CASCADE, related_name='logs')
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='status_changes')
    status = models.CharField(max_length=20)
    remarks = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.grievance.title} -> {self.status}"
