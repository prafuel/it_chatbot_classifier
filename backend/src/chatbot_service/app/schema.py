import uuid
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, Dict, List


"""
{
"status": "success",
  "ip": "125.21.222.34",
  "location": {
    "country": "India",
    "countryCode": "IN",
    "region": "Maharashtra",
    "regionCode": "MH",
    "city": "Pune",
    "zip": "411005",
    "coordinates": {
      "lat": 18.5211,
      "lon": 73.8502
    },
    "timezone": "Asia/Kolkata"
  },
  "network": {
    "isp": "BHARTI",
    "organization": "Bharti Televentures Ltd.",
    "asn": "AS9498 BHARTI Airtel Ltd."
  }

}
"""

class Chat(BaseModel):
    query: str
    response: str

class UserLocationData(BaseModel):
    country: Optional[str]
    countryCode: Optional[str]
    region: Optional[str]
    regionCode: Optional[str]
    city: Optional[str]
    zip: Optional[str]
    coordinates: Optional[dict]
    timezone: Optional[str]

class UserNetworkData(BaseModel):
    isp: Optional[str]
    organization: Optional[str]
    asn: Optional[str]

class UserData(BaseModel):
    status: Optional[str]
    ip: Optional[str]
    location: Optional[UserLocationData]
    network: Optional[UserNetworkData]

class ChatbotRequest(BaseModel):
    user_data: UserData
    query: str
    email: str

class ChatbotResponse(BaseModel):
    response: str

class BuildRequest(BaseModel):
    url: str

class BuildResponse(BaseModel):
    message: str
    intermediate_folder: str
    final_output_file: str

class WebExtractionSchema(BaseModel):
    url: str
    extracted_sitemap_urls: str
    extracted_urls: str
    urls_content: str

class GraphBotSchema(BaseModel):
    urls_content: str
    csv_output: str
    output_pkl: str
    output_tree: str
    output_flat: str

class ChatSessionResponse(BaseModel):
    id: uuid.UUID
    ip: Optional[str]
    country: Optional[str]
    country_code: Optional[str]
    region: Optional[str]
    region_code: Optional[str]
    city: Optional[str]
    zip: Optional[str]
    lat: Optional[float]
    lon: Optional[float]
    timezone: Optional[str]
    isp: Optional[str]
    organization: Optional[str]
    asn: Optional[str]
    chats: List[Chat]
    created_at: datetime

    class Config:
        from_attributes = True


class FilterableColumnsResponse(BaseModel):
    """List of column names available for filtering."""
    columns: list[str]


class ColumnValuesResponse(BaseModel):
    """Distinct values found in a specific column."""
    column: str
    values: list[str]


class ChatsFilterRequest(BaseModel):
    """
    Request body for POST /chats/filter.

    `filters` is a mapping of column_name → value.
    All provided pairs are ANDed together. Pass an empty dict to return all chats.
    """
    filters: dict[str, str] = {}
    sort_by: Optional[str] = None
    sort_type: Optional[str] = "desc"  # "asc" or "desc"

class FilteredChatsResponse(BaseModel):
    """
    Response body for filtered chat sessions.
    """
    chats: list[ChatSessionResponse]
    total_count: int

class AdminTextRequest(BaseModel):
    """Admin request to ingest extra textual knowledge."""
    text: str


class AdminTextResponse(BaseModel):
    """Response after ingesting admin text into FAISS."""
    message: str
    num_chunks: int
    index_path: str
