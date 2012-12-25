from django.contrib.auth.models import User
from auth.models import UserProfile

for user in User.objects.all():
    user_profile = UserProfile()
    user_profile.user = user
    user_profile.save()