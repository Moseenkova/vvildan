from .database import Airport, Request as TravelRequest
from .schemas import RequestSchema


def request_to_schema(request: TravelRequest) -> RequestSchema:
    def airport_data(airport: Airport) -> dict:
        return {
            "id": airport.id,
            "name": airport.name,
            "iata_code": airport.iata_code,
            "city_name": airport.city.name,
            "country_name": airport.city.country.name,
        }

    return RequestSchema(
        id=request.id,
        role=request.role.value,
        date_from=request.date_from,
        date_to=request.date_to,
        departure_airports=[airport_data(item) for item in request.departure_airports],
        arrival_airports=[airport_data(item) for item in request.arrival_airports],
        comment=request.comment,
        status=request.status.value,
        created_at=request.created_at,
    )
