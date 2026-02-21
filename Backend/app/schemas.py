from pydantic import BaseModel, Field, field_validator


class PredictRequest(BaseModel):
    seller_id: int = Field(gt=0)
    is_verified_seller: bool
    item_id: int = Field(gt=0)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    category: int = Field(gt=0)
    images_qty: int = Field(ge=0)

    @field_validator("images_qty")
    @classmethod
    def validate_images_qty(cls, value: int) -> int:
        if value < 0:
            raise ValueError("images_qty must be >= 0")
        return value


class PredictResponse(BaseModel):
    is_violation: bool
    probability: float


class SimplePredictRequest(BaseModel):
    item_id: int = Field(gt=0)


class AsyncPredictResponse(BaseModel):
    task_id: int
    status: str
    message: str
