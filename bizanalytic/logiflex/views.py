from django.shortcuts import render
from django.views.generic import (
    UpdateView,
    RedirectView,
    CreateView,
    View,
    TemplateView,
    DetailView,
    ListView,
    DeleteView,
)
# Create your views here.
class IndexView(TemplateView):
    template_name = "../templates/logiflex/index.html"