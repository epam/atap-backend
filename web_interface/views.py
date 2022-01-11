import os

from celery import states
from django.contrib.auth import authenticate, login
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django_celery_results.models import TaskResult

from web_interface.apps.task.tasks import test_page


def trigger_error(request):
    division_by_zero = 1 / 0


@csrf_exempt
def test_single_page(request):
    if request.method == 'POST':
        print('Requesting page test on ' + request.POST['url'])
        result = test_page.delay(request.POST['url'])
        return HttpResponse(result.task_id)

    if request.method == 'GET':
        task_id = request.GET['task_id']

        result = TaskResult.objects.get(task_id=task_id)

        if result.status != states.SUCCESS:
            return HttpResponse(result.status)
        else:
            filename = f'reports/{task_id}-report.pdf'
            if os.path.exists(filename):
                with open('report.pdf', 'rb') as fh:
                    response = HttpResponse(fh.read(), content_type='application/pdf')
                    response['Content-Disposition'] = 'inline; filename=' + os.path.basename(filename)
                    return response


def log_in(request):
    if request.POST:
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
    return render(request, 'login.html')
