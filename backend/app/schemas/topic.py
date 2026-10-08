from pydantic import BaseModel, ConfigDict

class TopicSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    topic_id: int
    slug: str
    name: str
    symbol: str

class TopicResponse(TopicSummary):
    vocabulary_count: int
