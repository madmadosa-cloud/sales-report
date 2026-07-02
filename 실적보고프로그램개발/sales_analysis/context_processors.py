"""템플릿 전역 컨텍스트"""

from sales_analysis.constants import APP_AUTHOR, APP_LICENSE, APP_VERSION


def app_meta(request):
    return {
        "app_version": APP_VERSION,
        "app_author": APP_AUTHOR,
        "app_license": APP_LICENSE,
    }
