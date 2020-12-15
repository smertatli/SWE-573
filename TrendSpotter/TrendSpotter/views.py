from django.views.generic import TemplateView

class HomePage(TemplateView):
    template_name='homepage.html'
    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(TemplateView, self).get_context_data(**kwargs)
        context['loggedInUser'] = self.request.user
        return context