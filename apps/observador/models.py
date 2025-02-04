from django.db import models

class FolderMonitor(models.Model):
    path = models.CharField(max_length=255, unique=True)
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.path} (Procesado: {self.processed})"