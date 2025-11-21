#define BoutsResponse type
from typing import TypedDict, List, Optional

class ResponseLinks(TypedDict):
	first: str
	last: str
	next: Optional[str]
	prev: Optional[str]

class ResponseMeta(TypedDict):
	total: int

class ObjectData[A](TypedDict):
	id: str
	attributes: A

class EventAttributes(TypedDict):
	startDateTime: str
	state: str
	name: str
	location: str

class BoutAttributes(TypedDict):
	topWrestlerId: str
	bottomWrestlerId: str
	winnerWrestlerId: Optional[str]
	result: Optional[str]
	winType: Optional[str]
	eventId: str
	weightClassId: str
	
class WrestlerAttributes(TypedDict):
	firstName: str
	lastName: str
	state: str
	divisionId: str
	teamId: str
	grade: Optional[int]
	weightClassId: str
	dateOfBirth: Optional[str]
	identityPersonId: str
	isWeighInOk: Optional[bool]

class GenericResponse[T](TypedDict):
	data: List[ObjectData[T]]
	included: List[dict]
	links: ResponseLinks
	meta: ResponseMeta

BoutsResponse = GenericResponse[BoutAttributes]
WrestlersResponse = GenericResponse[WrestlerAttributes]