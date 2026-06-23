from typing import Any, List, Optional
from datetime import datetime

from pydantic import Field

from ninja import NinjaAPI, Schema, FilterSchema, Query
from ninja.throttling import AnonRateThrottle, AuthRateThrottle
from ninja.pagination import paginate, PaginationBase

from .models import Course

apiv2 = NinjaAPI(
    title="LMS API v2",
    version="2.0",
    urls_namespace="apiv2",
    throttle=[
        AnonRateThrottle('10/m'),
        AuthRateThrottle('100/m'),
    ],
)


# =========================
# SCHEMA COURSE (v2)
# =========================
class TeacherOut(Schema):
    id: int
    username: str
    email: str


class CourseOut(Schema):
    id: int
    name: str
    description: str
    price: int
    image: Optional[str] = None
    teacher: TeacherOut
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_image(obj):
        return obj.image.url if obj.image else None


# =========================
# FILTER COURSE (v2)
# =========================
class CourseFilter(FilterSchema):
    search: Optional[str] = Field(
        None, q=['name__icontains', 'description__icontains']
    )
    price: Optional[int] = Field(None, q='price')
    price_gte: Optional[int] = Field(None, q='price__gte')
    price_lte: Optional[int] = Field(None, q='price__lte')
    created_gte: Optional[datetime] = Field(None, q='created_at__gte')
    created_lte: Optional[datetime] = Field(None, q='created_at__lte')


# =========================
# PAGINATION (v2)
# =========================
class CoursePagination(PaginationBase):
    class Input(Schema):
        skip: int = 0
        limit: int = 5

    class Output(Schema):
        items: List[Any]
        total: int
        per_page: int

    def paginate_queryset(self, queryset, pagination: Input, **params):
        skip = pagination.skip
        limit = pagination.limit

        return {
            'items': queryset[skip: skip + limit],
            'total': queryset.count(),
            'per_page': limit,
        }


# =========================
# LIST COURSES (search + filter + sort + pagination)
# =========================
SORT_FIELDS = {
    'id', '-id',
    'name', '-name',
    'price', '-price',
    'created_at', '-created_at',
}


@apiv2.get('/courses', response=List[CourseOut])
@paginate(CoursePagination)
def list_courses(request, filters: CourseFilter = Query(...), sort: str = 'id'):
    courses = Course.objects.select_related('teacher').all()
    courses = filters.filter(courses)

    if sort in SORT_FIELDS:
        courses = courses.order_by(sort)

    return courses
