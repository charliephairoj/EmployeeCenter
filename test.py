from django.contrib.staticfiles.views import serve

def display(request):
    return serve(request, 'https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/DRLogo.jpg')