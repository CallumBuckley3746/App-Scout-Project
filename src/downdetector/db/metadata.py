from downdetector.db.base import Base
from downdetector.db.breach import Breach as Breach
from downdetector.db.check import Check as Check
from downdetector.db.check_attempt import CheckAttempt as CheckAttempt
from downdetector.db.check_state import CheckState as CheckState
from downdetector.db.incident import Incident as Incident
from downdetector.db.outbox import OutboxEvent as OutboxEvent
from downdetector.db.service import Service as Service
from downdetector.db.service_card import ServiceCard as ServiceCard
from downdetector.db.user import User as User

metadata = Base.metadata
