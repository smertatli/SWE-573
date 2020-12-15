from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from .forms import UserForm
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse_lazy, reverse
from django.conf import settings
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import io
import re
import twitter
from collections import OrderedDict
from .fusioncharts import FusionCharts

CONSUMER_KEY = "sJJJUWkvfvpZYcbY0buMRYup7"
CONSUMER_SECRET = "iDQB0WGuOsY7ITZCYwZEk2o7a2kxiSKn6kFg3NZFO4ca11LoYA" 
ACCESS_TOKEN = "184983841-Cg8ps0f6pp98lsQRwennlwhilmHpMFQp2TUuciH1"
ACCESS_TOKEN_SECRET = "an8rfv4cyuSLCCaUqfU3zy8RRS55hmGHUvim1FGDJkQlk"


def is_email_occupied(_email):
    user = User.objects.filter(username=_email).exists()
    if user:
        return True
    else:
        return False


def _signup(request):
    error=''
    if request.method == 'POST':
        form = UserForm(data = request.POST)
        if is_email_occupied(request.POST.get('email')):
            error = 'Email is in use. Please provide a different email.'

        elif form.is_valid():
            user = form.save()
            password = request.POST.get('password')
            user.set_password(password)
            user.save()
            return redirect(settings.LOGIN_URL)
        else:
            error = 'Form validation failed.' 

    return render(request, 'accounts/signup.html', {
        'error': error 
    })


def _login(request):
    loginFailed = False
    errorMessage = ""
    if request.user.is_authenticated:
        return render(request, 'accounts/board.html')
    elif request.method == 'POST':
        username = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user:
            if user.is_active:
                login(request, user)
                return render(request, 'accounts/board.html')
            else:
                loginFailed = True
                errorMessage = "Your account is not active"
                # return HttpResponse("Your account is not active.")
        else:
            loginFailed = True
            errorMessage = "Invalid login,check your username and password!"
    return render(request, 'accounts/login.html', {'loginFailed': loginFailed,
                                                   'errorMessage': errorMessage
                                                   })
@login_required
def _looknfeel(request):
    return render(request, 'accounts/looknfeel.html')

@csrf_exempt
def _sniff_tweets(request):
    keyword = request.POST.get('keyword')
    start_date = request.POST.get('start')
    end_date = request.POST.get('end')
    api = twitter.Api(consumer_key=CONSUMER_KEY,
                  consumer_secret=CONSUMER_SECRET,
                  access_token_key=ACCESS_TOKEN,
                  access_token_secret=ACCESS_TOKEN_SECRET)
    data = api.GetSearch(term=keyword, count=100, lang='tr', since=start_date, until=end_date ,  include_entities=False, result_type='recent')
    tweets_text = [[tw.id,tw.created_at,tw.text] for tw in data]
    tweets_text = {'data': tweets_text}
    
    return JsonResponse(tweets_text, safe=False)





def myFirstChart(request):
# Chart data is passed to the `dataSource` parameter, like a dictionary in the form of key-value pairs.
  dataSource = OrderedDict()

# The `chartConfig` dict contains key-value pairs of data for chart attribute
  chartConfig = OrderedDict()
  chartConfig["caption"] = "Countries With Most Oil Reserves [2017-18]"
  chartConfig["subCaption"] = "In MMbbl = One Million barrels"
  chartConfig["xAxisName"] = "Country"
  chartConfig["yAxisName"] = "Reserves (MMbbl)"
  chartConfig["numberSuffix"] = "K"
  chartConfig["theme"] = "fusion"

  dataSource["chart"] = chartConfig
  dataSource["data"] = []

 # The data for the chart should be in an array wherein each element of the array  is a JSON object having the `label` and `value` as keys.
# Insert the data into the `dataSource['data']` list.
  dataSource["data"].append({"label": 'Venezuela', "value": '290'})
  dataSource["data"].append({"label": 'Saudi', "value": '290'})
  dataSource["data"].append({"label": 'Canada', "value": '180'})
  dataSource["data"].append({"label": 'Iran', "value": '140'})
  dataSource["data"].append({"label": 'Russia', "value": '115'})
  dataSource["data"].append({"label": 'Russia', "value": '115'})
  dataSource["data"].append({"label": 'UAE', "value": '100'})
  dataSource["data"].append({"label": 'US', "value": '30'})
  dataSource["data"].append({"label": 'China', "value": '30'})

# Create an object for the column 2D chart using the FusionCharts class constructor
# The chart data is passed to the `dataSource` parameter.
  column2D = FusionCharts("column2d", "myFirstChart", "600", "400", "myFirstchart-container", "json", dataSource)
  return render(request, 'accounts/board.html', {
    'output': column2D.render()
})


