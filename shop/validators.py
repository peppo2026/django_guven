from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class LetterAndNumberPasswordValidator:
    def validate(self, password, user=None):
        has_letter = any(char.isalpha() for char in password)
        has_number = any(char.isdigit() for char in password)

        if not has_letter or not has_number:
            raise ValidationError(
                _("Şifre en az 1 harf ve 1 rakam içermelidir."),
                code="password_no_letter_or_number",
            )

    def get_help_text(self):
        return _("Şifreniz en az 1 harf ve 1 rakam içermelidir.")