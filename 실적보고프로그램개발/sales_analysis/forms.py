from django import forms



from sales_analysis.constants import (

    CATEGORY_CODE_ERROR,

    CATEGORY_CODE_PATTERN,

    MASTER_UPLOAD_MODE_MERGE,

    MASTER_UPLOAD_MODE_REPLACE,

)





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





class CategoryMasterForm(forms.Form):

    code = forms.CharField(

        max_length=1,

        label="코드",

        help_text="영문 소문자 1글자 (a~z)",

    )

    name = forms.CharField(max_length=64, label="분류명")

    is_active = forms.BooleanField(required=False, initial=True, label="사용")



    def clean_code(self):

        import re



        code = (self.cleaned_data.get("code") or "").strip().lower()

        if not re.match(CATEGORY_CODE_PATTERN, code):

            raise forms.ValidationError(CATEGORY_CODE_ERROR)

        return code



    def clean_name(self):

        name = (self.cleaned_data.get("name") or "").strip()

        if not name:

            raise forms.ValidationError("분류명을 입력하세요.")

        return name





class CategoryMasterUploadForm(forms.Form):

    UPLOAD_MODE_CHOICES = [

        (MASTER_UPLOAD_MODE_MERGE, "기존 유지 + 새 코드 추가·이름 수정 (권장)"),

        (MASTER_UPLOAD_MODE_REPLACE, "전체 교체 (기존에 없는 코드는 삭제)"),

    ]



    file = forms.FileField(label="분류코드 CSV", widget=forms.ClearableFileInput(attrs={"accept": ".csv"}))

    mode = forms.ChoiceField(

        choices=UPLOAD_MODE_CHOICES,

        initial=MASTER_UPLOAD_MODE_MERGE,

        label="업로드 방식",

        widget=forms.RadioSelect,

    )




class WelfareOutputItemForm(forms.Form):
    code = forms.CharField(
        max_length=32,
        label="내부코드",
        help_text="영문 소문자로 시작 (예: facility, office)",
    )
    name = forms.CharField(max_length=64, label="출력항목")
    item_codes = forms.CharField(
        required=False,
        label="품목코드",
        help_text="쉼표·공백으로 구분 (예: o, q, t, u)",
    )
    sort_order = forms.IntegerField(required=False, min_value=0, label="정렬")
    is_active = forms.BooleanField(required=False, initial=True, label="사용")

    def clean_code(self):
        import re

        slug = (self.cleaned_data.get("code") or "").strip().lower()
        if not re.match(r"^[a-z][a-z0-9_]*$", slug):
            raise forms.ValidationError(
                "내부코드는 영문 소문자로 시작하고, 영문·숫자·밑줄만 사용할 수 있습니다."
            )
        return slug

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("출력항목명을 입력하세요.")
        return name

    def clean_item_codes(self):
        from sales_analysis.services.welfare_service import parse_item_codes

        raw = self.cleaned_data.get("item_codes") or ""
        try:
            codes = parse_item_codes(raw)
        except ValueError as exc:
            raise forms.ValidationError(str(exc)) from exc
        return ", ".join(codes)

