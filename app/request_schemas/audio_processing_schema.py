from pydantic import BaseModel


class AudioProcessRequest(BaseModel):
    file_path: str


class AudioProcessResponse(BaseModel):
    status: str
    input_path: str
    output_path: str
    operation: str
