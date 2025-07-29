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
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse, reverse_lazy

from . import models, forms

# Create your views here.


class IndexView(TemplateView):
    template_name = "../templates/logiflex/home.html"


class NewsletterCreateView(UserPassesTestMixin, CreateView):
    model = models.NewsLetter_logiflex
    form_class = forms.NewsLetter_logiflexForm
    success_url = reverse_lazy("logiflex:index")

    def test_func(self):
        return self.request.user.is_staff


class NewsletterListView(UserPassesTestMixin, ListView):
    model = models.NewsLetter_logiflex
    template_name = ""

    def test_func(self):
        return self.request.user.is_staff


