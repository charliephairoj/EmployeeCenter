# Create your views here.
from django.conf import settings
from library.models import Book
import json
from django.http import HttpResponseRedirect, HttpResponse

def book(request):
    
    if request.method == "GET":
        
        books = Book.objects.all()
        data=[]
        for book in books:
            data.append({'url':book.url, 'id':book.id})
            
        response = HttpResponse(json.dumps(data), mimetype="application/json")
        return response
    elif request.method == "POST":
        #extract data and converts to object
        data = json.loads(request.POST.get('data'))
        
        #extract the file and the filename
        image = request.FILES['image']
        filename = settings.MEDIA_ROOT+image.name
        
        #write the file to disk
        with open(filename, 'wb+' ) as destination:
            for chunk in image.chunks():
                destination.write(chunk)
                
        
        book = Book()
        if "description" in data: book.description = data["description"]
        if "category" in data: book.category = data["category"]
        data = book.upload(filename)
        
        
        
        response = HttpResponse(json.dumps(data), mimetype="application/json")
        response.status_code = 201
        return response