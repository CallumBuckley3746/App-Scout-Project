This is a backend review of the solution. The product shows the status of third-party services. The engineering problem is different: a third-party site responds slowly, a dropped connection is easy to mistake for an outage, and our own page has to stay fast and must not raise an alert because of a single network failure.

Discord, WhatsApp, and YouTube are the first rows in the catalog. Another service is added as a catalog row, with no new deployment, when a check already exists for that kind of source. Who talks to whom is shown in the overall diagram.

Stack

Everything below follows from how these parts are split. A visitor reaches FastAPI only. A call to a third-party site runs in another process.

The site and the stream for an already open tab are FastAPI. That request stays short and does not call third-party services. Pydantic defines the check result, so an HTTP check, a status page, and the breach catalog all return the same shape. PostgreSQL is reached through SQLAlchemy 2 and asyncpg, asynchronously, in the same style as the API. Alembic owns the schema, and migrations ship with the code.

What must not be lost lives in PostgreSQL: the catalog, the check log, cards, incidents, and outbound notifications. Redis holds the job queue and the signal to an open tab. That data is short-lived, not the statuses themselves. Background checks run on Taskiq, outside the visitor's request. Outbound calls go through httpx, an asynchronous client with a timeout. Docker Compose starts the whole set: the site, the scheduler, the worker, PostgreSQL, and Redis.

Docker Compose brings those five parts up with one command.

A visitor opens FastAPI. FastAPI reads the card from PostgreSQL and can push a Redis signal to a tab that is already open. That request does not call YouTube or Discord.

The scheduler puts due checks on the Redis queue. A Taskiq worker takes the job and calls out through httpx with a hard timeout. Taskiq has the same role as Celery, but the jobs stay asynchronous, in the same style as FastAPI. Pydantic gives every check result the same shape, and that result is written to PostgreSQL. Alembic ships the schema with the code.

PostgreSQL keeps what must survive a restart: the catalog, the check log, the current card, incidents, and the notification queue. Redis keeps the job queue and a short "the card has changed" signal. Statuses are not written to Redis. If Redis is flushed, the cards remain in PostgreSQL and checks resume on the scheduler's next tick. If MySQL is required instead of PostgreSQL, only the primary database engine changes. Redis stays for the queue and for the signal to open tabs.

Checks run from a single machine. A break on our path to YouTube looks like a YouTube outage. Three failures in a row reduce that risk. A second geographic vantage point is not part of the first version. How these parts connect is shown in the stack diagram.

What follows from that split

The stack already separates a visitor request from a call to a third-party service. While YouTube does not respond, the site keeps serving the previous status from PostgreSQL.

A raw response and the status on the card are also different things. The httpx check only records a fact. A separate step decides whether the state changed. The site is notified on that transition.

How an availability check works

Each check maps the remote response to one of four results: success, slow, failure, or unknown. The state machine then uses only that result. It does not matter whether the response came from Discord or from a site that was added a moment ago.

If the service has an official status page, we read that page. Discord and many other companies publish summary.json with a status such as all systems operational, partial outage, or major outage. The vendor has already confirmed a major outage, so one response is enough for that check. A partial outage moves the card to degraded.

If there is no status page, httpx requests the public URL. That is how YouTube, WhatsApp Web, and any URL an administrator added by link are checked. For YouTube we use the lightweight generate_204 endpoint, and the homepage if that endpoint does not answer as expected. For WhatsApp we use web.whatsapp.com. A successful response means up, a slow one means degraded, and a dropped connection or an HTTP 5xx counts as a failure. The card becomes down after three failures in a row and up again after two successes in a row. Until the threshold is reached, the site keeps the last confirmed status, and the card does not flicker. The card transitions are shown in the state diagram.

A response that says "slow down, you are calling too often" is not recorded as a failure of their service. That is our request rate, not an outage on their side. The attempt stays in the log as an unknown result and does not change the state.

The interval and the thresholds live on the check row, not in code. Our own HTTP request runs once a minute by default. An official status page can be polled less often.

Security is a second path, with a different cadence and a different meaning. Once an hour the same worker queries the Have I Been Pwned breach catalog for the service domain. A newly published breach sets a separate badge. Availability can stay up: a breach and an outage are independent facts. The request shows a breach that has already been published, not an intrusion at the moment it happens. Both views of one service are shown in the availability and breach diagram.

What must not be lost, and what must not be counted twice

Running the same check again must not increment the failure counter a second time. Each attempt has its own time slot. A job redelivered from Redis lands in that same slot instead of creating a new failure.

The visible status change, the incident, and the record "the site must be notified" are saved in one PostgreSQL transaction. That is the outbox: the event for the site is stored next to the incident and waits to be picked up. If the notification worker stops after the transaction has committed, the row stays unread and the next pass picks it up. Restarting the process does not erase the alert.

An open tab listens for a Redis signal and updates the card at once. That signal can be lost, because a Redis channel keeps no history. When the tab connects, it therefore reads the current state from PostgreSQL first and only then listens to the stream. The path from a repeated failure to the card on the site is shown in the notification diagram.

The transition engine is a pure function. It takes the current state, the new result, and the thresholds, and it returns a decision to stay or to change status. It can be tested with no network and no database. This is the most fragile part of the product, and it does not belong in FastAPI handlers.

The catalog and third-party URLs

There are no code branches named Discord or YouTube. The worker looks at the check type and calls the matching module: HTTP, status page, RSS, or the breach catalog. A new site with a public URL or a status page is one row in the catalog. A new module is written only for a response format we do not handle yet. After that, further services of the same format are added as rows again.

An administrator adds the URL to the catalog. The worker requests that URL from our machine, so an anonymous visitor is not allowed to submit it. Only https to a public host is accepted. Localhost, private networks, and redirects to those addresses are rejected. Otherwise the "add a service" form would become a way to reach the internal network.

Each service has one primary check, and that check decides the card status. An extra URL can move the card to degraded. A breach check does not change availability. How a new service shows up on the site is shown in the new-service diagram.
