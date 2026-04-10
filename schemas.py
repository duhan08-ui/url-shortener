from pydantic import BaseModel, HttpUrl

class URLBase(BaseModel):
    original_url: HttpUrl

class URLResponse(BaseModel):
    short_url: str
    original_url: str

    class Config:
        from_attributes = True