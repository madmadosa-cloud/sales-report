from django import forms


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={"accept": ".csv"}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        if not data:
            if self.required:
                raise forms.ValidationError(self.error_messages["required"])
            return []
        if not isinstance(data, (list, tuple)):
            data = [data]
        return data


class SalesUploadForm(forms.Form):
    files = MultipleFileField(label="매출자료 CSV", required=True)


class ReportPeriodForm(forms.Form):
    PRESET_CHOICES = [
        ("first_half", "상반기 (1~6월)"),
        ("second_half", "하반기 (7~12월)"),
        ("full_year", "연간 (1~12월)"),
        ("custom", "직접 입력"),
    ]

    year = forms.IntegerField(min_value=2000, max_value=2100, initial=2025, label="연도")
    preset = forms.ChoiceField(choices=PRESET_CHOICES, initial="first_half", label="기간")
    start_month = forms.IntegerField(min_value=1, max_value=12, initial=1, required=False, label="시작월")
    end_month = forms.IntegerField(min_value=1, max_value=12, initial=6, required=False, label="종료월")

    def clean(self):
        cleaned = super().clean()
        preset = cleaned.get("preset")
        if preset == "first_half":
            cleaned["start_month"] = 1
            cleaned["end_month"] = 6
        elif preset == "second_half":
            cleaned["start_month"] = 7
            cleaned["end_month"] = 12
        elif preset == "full_year":
            cleaned["start_month"] = 1
            cleaned["end_month"] = 12
        else:
            start = cleaned.get("start_month")
            end = cleaned.get("end_month")
            if start is None or end is None:
                raise forms.ValidationError("시작월과 종료월을 입력하세요.")
            if start > end:
                raise forms.ValidationError("시작월이 종료월보다 클 수 없습니다.")
        return cleaned
