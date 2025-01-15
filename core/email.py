from djoser import email

class PasswordResetEmailTemplate(email.PasswordResetEmail):
    template_name = "email/password_reset_email.html"