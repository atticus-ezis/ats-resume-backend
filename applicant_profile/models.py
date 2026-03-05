import hashlib
import json

from django.contrib.auth.models import User
from django.db import models

CONSTRAINT_UNIQUE_CONTEXT = "unique_context_per_user"
CONSTRAINT_UNIQUE_NAME = "unique_name_per_user"


def compute_context_hash(value):
    """Return SHA256 hex digest for context value (string or JSON-serializable)."""
    if isinstance(value, str):
        data = value.encode("utf-8")
    else:
        data = json.dumps(value, sort_keys=True).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


# User Context Model
class UserContext(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="resumes")
    name = models.CharField(max_length=255)
    context = models.JSONField()
    context_hash = models.CharField(max_length=64, db_index=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.context is not None:
            self.context_hash = compute_context_hash(self.context)
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "context_hash"],
                name=CONSTRAINT_UNIQUE_CONTEXT,
            ),
            models.UniqueConstraint(
                fields=["user", "name"],
                name=CONSTRAINT_UNIQUE_NAME,
            ),
        ]
