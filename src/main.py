# uvicorn src.main:app --reload --reload-dir src --host 0.0.0.0 --port 8001

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from src.database import async_session_maker, City, Country
from src.schemas import CitySchema, CountrySchema, RequestCreateSchema

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/countries", response_model=list[CountrySchema])
async def get_countries(q: str = Query("", description="Search countries by name")):
    async with async_session_maker() as session:
        query = select(Country).order_by(Country.name.asc())
        if q.strip():
            query = query.where(Country.name.ilike(f"%{q.strip()}%"))
        result = await session.execute(query)
        countries = result.scalars().all()
        return countries


@app.get("/api/cities", response_model=list[CitySchema])
async def get_cities(
    country_id: int = Query(..., description="Country ID"),
    q: str = Query("", description="Search cities by name"),
):
    async with async_session_maker() as session:
        query = (
            select(City)
            .where(City.country_id == country_id)
            .order_by(City.name.asc())
        )
        if q.strip():
            query = query.where(City.name.ilike(f"%{q.strip()}%"))
        result = await session.execute(query)
        cities = result.scalars().all()
        return cities


@app.post("/api/requests")
async def create_request(body: RequestCreateSchema):
    print(body)
    """Accept request creation from the web form."""
    # For now, return the validated payload. Wire to DB (Request, UserCity, etc.) as needed.
    return {"ok": True, "data": body.model_dump()}


'''
1 создать страны и города если нет в списке
2 найти пользователя через тг айди и добавить если не было
3 создать заявку


пример данных
{
  "role":"sender",
  "date_from":"09.08.2026",
  "date_to":"10.08.2026",
  "date":null,
  "country_from": {
    "id":2, айди если есть в базе
    "name":"United Kingdom"
  },
  "city_from":{
    "id":null, если айди нет - то надо добавить этот город к стране
    "name":"London"
  },
  "country_to":{
    "id":null, нет айди страны - добавить страну
    "name":"Россия"
  },
  "city_to":{
    "id":null, нет айди города - добавить годор к добавленной стране
    "name":"Уфа" 
  },
  "comment":"",
  "telegram_id":5875912525 что бы найти пользователя
}


'''