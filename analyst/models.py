from django.db import models

class Dataset(models.Model):
    file = models.FileField(upload_to='datasets/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    profile_data = models.JSONField(null=True, blank=True)
    kpi_data = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"Dataset {self.id} - {self.file.name}"
