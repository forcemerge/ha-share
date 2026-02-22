(() => {
  const CARD_TYPE = "notion-travel-trip-card";
  const ALIAS_CARD_TYPE = "notion-travel-trip-card-v2";
  const DEFAULT_ENTITY = "sensor.notion_travel_next_trip";

  const BAD_STATES = new Set(["unknown", "unavailable", "none", ""]);
  const COST_DISPLAY_MIN = 0.01;

  const DATASET_LABEL = {
    flights: "Flight",
    lodging: "Stay",
    transportation: "Transit",
    activities: "Activity",
    dining: "Dining",
    notes: "Note",
  };

  function esc(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function toNum(value) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  function toDate(value) {
    if (!value) {
      return null;
    }
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }

  function fmtDate(value) {
    const d = toDate(value);
    if (!d) {
      return "—";
    }
    return new Intl.DateTimeFormat(undefined, {
      weekday: "short",
      month: "short",
      day: "numeric",
    }).format(d);
  }

  function fmtDateShort(value) {
    const d = toDate(value);
    if (!d) {
      return "—";
    }
    return new Intl.DateTimeFormat(undefined, {
      month: "short",
      day: "numeric",
    }).format(d);
  }

  function fmtTime(value, timeZone) {
    const raw = String(value || "");
    if (!raw || raw.indexOf("T") === -1) {
      return "Any time";
    }

    const wallClock = raw.match(/T(\d{2}):(\d{2})/);
    const d = toDate(value);
    if (!d) {
      return "Any time";
    }

    // Prefer explicit Notion timezone when provided.
    if (timeZone) {
      try {
        return new Intl.DateTimeFormat(undefined, {
          hour: "numeric",
          minute: "2-digit",
          timeZone,
        }).format(d);
      } catch (_err) {
        // Fall through to wall-clock fallback below.
      }
    }

    // If Notion encoded an offset in the timestamp but did not provide
    // an IANA timezone string, preserve the configured local wall time.
    if (wallClock) {
      const hh = Number(wallClock[1]);
      const mm = Number(wallClock[2]);
      const wallDate = new Date(Date.UTC(2000, 0, 1, hh, mm, 0));
      return new Intl.DateTimeFormat(undefined, {
        hour: "numeric",
        minute: "2-digit",
        timeZone: "UTC",
      }).format(wallDate);
    }

    return new Intl.DateTimeFormat(undefined, {
      hour: "numeric",
      minute: "2-digit",
    }).format(d);
  }

  function fmtMoney(value) {
    const n = toNum(value);
    if (n === null) {
      return "—";
    }
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 2,
    }).format(n);
  }

  function dayLabel(dateObj) {
    return new Intl.DateTimeFormat(undefined, {
      weekday: "short",
      month: "short",
      day: "numeric",
    }).format(dateObj);
  }

  function relCountdown(days) {
    const n = toNum(days);
    if (n === null) {
      return "Date pending";
    }
    if (n < 0) {
      return "In progress";
    }
    if (n === 0) {
      return "Today";
    }
    return `T-${n} day${n === 1 ? "" : "s"}`;
  }

  class NotionTravelTripCard extends HTMLElement {
    setConfig(config) {
      if (!config) {
        throw new Error("Invalid configuration");
      }

      this._config = {
        entity: config.entity || DEFAULT_ENTITY,
        mode: config.mode || "hero",
        title: config.title || "",
        use_upcoming: config.use_upcoming !== false,
        show_past: Boolean(config.show_past),
        include_notes_in_timeline: Boolean(config.include_notes_in_timeline),
        max_events: Number.isFinite(config.max_events) ? Number(config.max_events) : 100,
        max_notes: Number.isFinite(config.max_notes) ? Number(config.max_notes) : 8,
      };

      this._ensureRoot();
      this._render();
    }

    set hass(hass) {
      this._hass = hass;
      this._render();
    }

    getCardSize() {
      if (!this._config) {
        return 6;
      }
      if (this._config.mode === "timeline") {
        return 11;
      }
      if (this._config.mode === "details") {
        return 8;
      }
      if (this._config.mode === "overview") {
        return 16;
      }
      return 6;
    }

    _ensureRoot() {
      if (this._root) {
        return;
      }

      this.attachShadow({ mode: "open" });

      const style = document.createElement("style");
      style.textContent = `
        :host {
          --nt-font: "Avenir Next", "Segoe UI", "Inter", sans-serif;
          --nt-bg-1: #111723;
          --nt-bg-2: #1b2435;
          --nt-card: rgba(255,255,255,0.06);
          --nt-border: rgba(255,255,255,0.12);
          --nt-text: #f4f7ff;
          --nt-muted: #b5c1d8;
          --nt-rail: #5b6d8d;
          --nt-accent: #57c0ff;
          --nt-good: #22c56d;
          --nt-warn: #f2b34c;
          --nt-danger: #ff6d6d;
          --nt-radius: 18px;
        }

        ha-card {
          overflow: hidden;
          border-radius: var(--nt-radius);
          color: var(--nt-text);
          border: 1px solid var(--nt-border);
          background: radial-gradient(120% 120% at 0% 0%, #22324f 0%, var(--nt-bg-1) 55%, #0f141f 100%);
          font-family: var(--nt-font);
        }

        .wrap {
          padding: 18px;
        }

        .title {
          font-size: 14px;
          text-transform: uppercase;
          letter-spacing: 0.09em;
          color: var(--nt-muted);
          margin-bottom: 10px;
        }

        .overview-grid {
          display: grid;
          grid-template-columns: minmax(300px, 1fr) minmax(420px, 1.35fr);
          gap: 14px;
          align-items: start;
        }

        .overview-left,
        .overview-right {
          display: grid;
          gap: 12px;
          align-content: start;
        }

        .hero {
          display: grid;
          grid-template-columns: 1fr auto;
          gap: 16px;
          align-items: center;
          border: 1px solid var(--nt-border);
          background: linear-gradient(135deg, rgba(87,192,255,0.14), rgba(19,30,51,0.7));
          border-radius: 16px;
          padding: 16px;
        }

        .hero-main {
          min-width: 0;
        }

        .trip-name {
          font-size: 28px;
          font-weight: 700;
          line-height: 1.06;
          margin: 0;
          overflow-wrap: anywhere;
        }

        .trip-meta {
          margin-top: 6px;
          color: var(--nt-muted);
          font-size: 14px;
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
          overflow-wrap: anywhere;
        }

        .hero-pill {
          font-size: 12px;
          font-weight: 700;
          border-radius: 999px;
          border: 1px solid var(--nt-border);
          background: rgba(255,255,255,0.08);
          padding: 6px 10px;
          align-self: start;
        }

        .hero-stats {
          margin-top: 14px;
          display: grid;
          gap: 8px;
        }

        .hero-stat {
          display: flex;
          justify-content: space-between;
          align-items: baseline;
          gap: 10px;
          border-radius: 14px;
          border: 1px solid var(--nt-border);
          background: var(--nt-card);
          padding: 10px 12px;
        }

        .hero-stat-full {
          width: 100%;
          background: rgba(87, 192, 255, 0.1);
        }

        .hero-stat-pair {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 8px;
        }

        .hero-stat-label {
          font-size: 11px;
          color: var(--nt-muted);
          text-transform: uppercase;
          letter-spacing: 0.06em;
          flex: 0 0 auto;
        }

        .hero-stat-value {
          font-size: 14px;
          font-weight: 700;
          overflow-wrap: anywhere;
          text-align: right;
        }

        .next-event {
          margin-top: 14px;
          border-radius: 14px;
          border: 1px solid var(--nt-border);
          background: rgba(31, 45, 70, 0.7);
          padding: 12px;
          width: 100%;
          box-sizing: border-box;
        }

        .next-event-head {
          color: var(--nt-muted);
          font-size: 11px;
          letter-spacing: 0.07em;
          text-transform: uppercase;
        }

        .next-event-title {
          margin-top: 5px;
          font-size: 16px;
          font-weight: 700;
          overflow-wrap: anywhere;
        }

        .next-event-sub {
          margin-top: 2px;
          color: var(--nt-muted);
          font-size: 13px;
          overflow-wrap: anywhere;
        }

        .timeline {
          display: grid;
          gap: 12px;
        }

        .day-block {
          border-radius: 16px;
          border: 1px solid var(--nt-border);
          background: rgba(18, 25, 39, 0.72);
          padding: 12px;
        }

        .day-label {
          font-size: 13px;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          color: var(--nt-muted);
          margin-bottom: 8px;
        }

        .event {
          display: grid;
          grid-template-columns: 78px 28px 1fr;
          gap: 10px;
          align-items: start;
          margin-top: 10px;
        }

        .event:first-of-type {
          margin-top: 0;
        }

        .time {
          font-size: 12px;
          color: var(--nt-muted);
          font-weight: 600;
          text-align: right;
          padding-top: 2px;
        }

        .rail {
          position: relative;
          min-height: 56px;
        }

        .rail::before {
          content: "";
          position: absolute;
          left: 13px;
          top: -10px;
          bottom: -10px;
          width: 2px;
          background: linear-gradient(180deg, transparent 0%, var(--nt-rail) 10%, var(--nt-rail) 90%, transparent 100%);
        }

        .dot {
          position: relative;
          z-index: 1;
          width: 26px;
          height: 26px;
          border-radius: 999px;
          border: 1px solid var(--nt-border);
          display: grid;
          place-items: center;
          background: #223557;
          color: #b4dfff;
        }

        .event-card {
          border-radius: 14px;
          border: 1px solid var(--nt-border);
          background: var(--nt-card);
          padding: 10px 11px;
        }

        .event-top {
          display: flex;
          justify-content: space-between;
          gap: 10px;
          align-items: baseline;
        }

        .event-title {
          font-size: 16px;
          font-weight: 700;
          line-height: 1.2;
          overflow-wrap: anywhere;
        }

        .tag {
          border-radius: 999px;
          border: 1px solid var(--nt-border);
          background: rgba(255,255,255,0.08);
          padding: 3px 8px;
          font-size: 11px;
          color: var(--nt-muted);
          text-transform: uppercase;
          letter-spacing: 0.06em;
        }

        .event-sub,
        .event-loc,
        .event-extra,
        .event-notes {
          margin-top: 4px;
          color: var(--nt-muted);
          font-size: 13px;
          overflow-wrap: anywhere;
        }

        .event-notes strong {
          color: var(--nt-text);
        }

        a.link {
          color: #8fd2ff;
          text-decoration: none;
          font-weight: 600;
        }

        a.link:hover {
          text-decoration: underline;
        }

        .details-grid {
          display: grid;
          grid-template-columns: 1fr;
          gap: 12px;
        }

        .panel {
          border-radius: 14px;
          border: 1px solid var(--nt-border);
          background: var(--nt-card);
          padding: 12px;
        }

        .panel h4 {
          margin: 0;
          font-size: 13px;
          text-transform: uppercase;
          letter-spacing: 0.07em;
          color: var(--nt-muted);
        }

        .panel ul {
          margin: 8px 0 0;
          padding-left: 18px;
          line-height: 1.5;
          font-size: 14px;
          overflow-wrap: anywhere;
        }

        .panel .meta {
          margin-top: 8px;
          color: var(--nt-muted);
          font-size: 14px;
          line-height: 1.55;
          overflow-wrap: anywhere;
        }

        .panel .meta strong {
          color: var(--nt-text);
        }

        .notes-list {
          list-style: none;
          margin: 8px 0 0;
          padding: 0;
          display: grid;
          gap: 8px;
        }

        .note-item {
          border-radius: 12px;
          border: 1px solid var(--nt-border);
          background: rgba(255,255,255,0.03);
          padding: 10px;
        }

        .note-title {
          font-size: 14px;
          font-weight: 700;
          overflow-wrap: anywhere;
        }

        .note-sub {
          margin-top: 3px;
          color: var(--nt-muted);
          font-size: 13px;
          overflow-wrap: anywhere;
        }

        .note-meta {
          margin-top: 4px;
          color: var(--nt-muted);
          font-size: 12px;
        }

        .empty {
          border-radius: 14px;
          border: 1px dashed var(--nt-border);
          background: rgba(255,255,255,0.04);
          color: var(--nt-muted);
          padding: 16px;
          text-align: center;
          font-size: 14px;
        }

        @media (max-width: 1200px) {
          .overview-grid {
            grid-template-columns: 1fr;
          }
        }

        @media (max-width: 900px) {
          .hero-stat-pair {
            grid-template-columns: 1fr;
          }

          .details-grid {
            grid-template-columns: 1fr;
          }

          .event {
            grid-template-columns: 60px 24px 1fr;
          }

          .trip-name {
            font-size: 22px;
          }
        }
      `;

      this._root = document.createElement("div");
      this.shadowRoot.append(style, this._root);
    }

    _stateObj() {
      if (!this._hass || !this._hass.states || !this._config) {
        return null;
      }
      return this._hass.states[this._config.entity] || null;
    }

    _events(attrs) {
      const source = this._config.use_upcoming
        ? attrs.timeline_events_upcoming || attrs.timeline_events
        : attrs.timeline_events;
      let events = Array.isArray(source) ? source : [];

      if (!this._config.include_notes_in_timeline) {
        events = events.filter((event) => String(event.dataset || "").toLowerCase() !== "notes");
      }

      if (!this._config.show_past) {
        const now = Date.now();
        events = events.filter((event) => {
          const start = toDate(event.start);
          const end = toDate(event.end);
          return (start && start.getTime() >= now) || (end && end.getTime() >= now);
        });
      }

      return events.slice(0, this._config.max_events);
    }

    _noteEvents(attrs) {
      const source = attrs.timeline_events;
      const events = Array.isArray(source) ? source : [];

      return events
        .filter((event) => String(event.dataset || "").toLowerCase() === "notes")
        .sort((a, b) => {
          const aDate = toDate(a.start) || toDate(a.end) || toDate(a.last_edited_time);
          const bDate = toDate(b.start) || toDate(b.end) || toDate(b.last_edited_time);
          const aTs = aDate ? aDate.getTime() : 0;
          const bTs = bDate ? bDate.getTime() : 0;
          return bTs - aTs;
        })
        .slice(0, this._config.max_notes);
    }

    _timelineStats(attrs) {
      const events = Array.isArray(attrs.timeline_events) ? attrs.timeline_events : [];
      const nonNotes = events.filter((event) => String(event.dataset || "").toLowerCase() !== "notes");
      const now = Date.now();
      const upcoming = nonNotes.filter((event) => {
        const start = toDate(event.start);
        const end = toDate(event.end);
        return (start && start.getTime() >= now) || (end && end.getTime() >= now);
      }).length;
      return {
        total: nonNotes.length,
        upcoming,
      };
    }

    _nextItineraryEvent(attrs) {
      const preferred = Array.isArray(attrs.timeline_events_upcoming) ? attrs.timeline_events_upcoming : [];
      const fallback = Array.isArray(attrs.timeline_events) ? attrs.timeline_events : [];
      const source = preferred.length ? preferred : fallback;
      const fallbackNext = attrs.next_event || null;

      const nonNotes = source.filter((event) => String(event.dataset || "").toLowerCase() !== "notes");
      if (!nonNotes.length) {
        if (fallbackNext && String(fallbackNext.dataset || "").toLowerCase() !== "notes") {
          return fallbackNext;
        }
        return null;
      }

      const ordered = nonNotes.slice().sort((a, b) => {
        const aDate = toDate(a.start) || toDate(a.end) || toDate(a.last_edited_time);
        const bDate = toDate(b.start) || toDate(b.end) || toDate(b.last_edited_time);
        const aTs = aDate ? aDate.getTime() : 0;
        const bTs = bDate ? bDate.getTime() : 0;
        return aTs - bTs;
      });

      return ordered[0] || fallbackNext || null;
    }

    _eventReferenceLabel(dataset) {
      const _ = dataset;
      return "Confirmation";
    }

    _groupEvents(events) {
      const grouped = [];
      const map = new Map();

      events.forEach((event) => {
        const eventDate = toDate(event.start) || toDate(event.end) || toDate(event.last_edited_time);
        const key = eventDate ? `${eventDate.getFullYear()}-${eventDate.getMonth()}-${eventDate.getDate()}` : "undated";
        if (!map.has(key)) {
          const block = {
            key,
            label: eventDate ? dayLabel(eventDate) : "Unscheduled",
            events: [],
          };
          map.set(key, block);
          grouped.push(block);
        }
        map.get(key).events.push(event);
      });

      return grouped;
    }

    _renderHero(stateObj, attrs) {
      const tripName = BAD_STATES.has(stateObj.state) ? "Notion Travel Offline" : stateObj.state;
      const destination = attrs.destination || "Destination TBD";
      const status = attrs.status || "Status unknown";
      const tags = Array.isArray(attrs.tags) ? attrs.tags.filter((tag) => Boolean(tag)) : [];
      const tagsLabel = tags.length ? tags.join(", ") : "—";
      const countdown = relCountdown(attrs.days_until_start);
      const start = fmtDate(attrs.start_date);
      const end = fmtDate(attrs.end_date);
      const totalCost = toNum(attrs.total_cost);
      const timelineStats = this._timelineStats(attrs);
      const timelineCount = timelineStats.total;
      const upcomingCount = timelineStats.upcoming;
      const nextEvent = this._nextItineraryEvent(attrs);
      const showSpend = totalCost !== null && totalCost > 0;

      return `
        <div class="hero">
          <div class="hero-main">
            <h2 class="trip-name">${esc(tripName)}</h2>
            <div class="trip-meta">
              <span>${esc(destination)}</span>
              <span>•</span>
              <span>${esc(status)}</span>
            </div>
            <div class="hero-stats">
              <div class="hero-stat hero-stat-full">
                <div class="hero-stat-label">Dates</div>
                <div class="hero-stat-value">${esc(start)} → ${esc(end)}</div>
              </div>
              <div class="hero-stat hero-stat-full">
                <div class="hero-stat-label">Plans</div>
                <div class="hero-stat-value">${timelineCount} total · ${upcomingCount} upcoming</div>
              </div>
              <div class="hero-stat hero-stat-full">
                <div class="hero-stat-label">Tags</div>
                <div class="hero-stat-value">${esc(tagsLabel)}</div>
              </div>
              ${showSpend ? `
                <div class="hero-stat hero-stat-full">
                  <div class="hero-stat-label">Spend</div>
                  <div class="hero-stat-value">${esc(fmtMoney(totalCost))}</div>
                </div>
              ` : ""}
            </div>
            ${nextEvent ? `
              <div class="next-event">
                <div class="next-event-head">Next on itinerary</div>
                <div class="next-event-title">${esc(nextEvent.title || "Untitled")}</div>
                <div class="next-event-sub">${esc(fmtDateShort(nextEvent.start || nextEvent.end))} • ${esc(fmtTime(nextEvent.start || nextEvent.end, nextEvent.time_zone))}${nextEvent.location ? ` • ${esc(nextEvent.location)}` : ""}</div>
              </div>
            ` : ""}
          </div>
          <div class="hero-pill">${esc(countdown)}</div>
        </div>
      `;
    }

    _renderTimeline(attrs) {
      const events = this._events(attrs);
      if (!events.length) {
        return '<div class="empty">No itinerary events available yet. Add date/time on child records in Notion to build the timeline.</div>';
      }

      const blocks = this._groupEvents(events)
        .map((block) => {
          const rows = block.events
            .map((event) => {
              const when = event.start || event.end;
              const datasetLabel = DATASET_LABEL[event.dataset] || event.dataset || "Event";
              const cost = toNum(event.cost);
              const showCost = cost !== null && cost > 0;
              const seat = String(event.seat || "").trim();
              const reference = String(event.confirmation || "").trim();
              const referenceLabel = this._eventReferenceLabel(String(event.dataset || ""));
              const notes = String(event.content || "").trim();
              const detailsUrl = String(event.notion_url || "").trim();
              const externalUrl = String(event.url || "").trim();
              return `
                <div class="event">
                  <div class="time">${esc(fmtTime(when, event.time_zone))}</div>
                  <div class="rail">
                    <div class="dot"><ha-icon icon="${esc(event.icon || "mdi:calendar-star")}"></ha-icon></div>
                  </div>
                  <div class="event-card">
                    <div class="event-top">
                      <div class="event-title">${esc(event.title || "Untitled")}</div>
                      <div class="tag">${esc(datasetLabel)}</div>
                    </div>
                    ${event.subtitle ? `<div class="event-sub">${esc(event.subtitle)}</div>` : ""}
                    ${event.location ? `<div class="event-loc">${esc(event.location)}</div>` : ""}
                    ${notes ? `<div class="event-notes"><strong>Notes:</strong> ${esc(notes)}</div>` : ""}
                    <div class="event-extra">
                      ${event.status ? `${esc(event.status)}` : "Status untracked"}
                      ${showCost ? ` • ${esc(fmtMoney(cost))}` : ""}
                      ${String(event.dataset || "") === "flights" && seat ? ` • Seat: ${esc(seat)}` : ""}
                      ${reference ? ` • ${esc(referenceLabel)}: ${esc(reference)}` : ""}
                      ${externalUrl ? ` • <a class="link" href="${esc(externalUrl)}" target="_blank" rel="noopener noreferrer">Link</a>` : ""}
                      ${detailsUrl ? ` • <a class="link" href="${esc(detailsUrl)}" target="_blank" rel="noopener noreferrer">Details</a>` : ""}
                    </div>
                  </div>
                </div>
              `;
            })
            .join("");

          return `
            <section class="day-block">
              <div class="day-label">${esc(block.label)}</div>
              ${rows}
            </section>
          `;
        })
        .join("");

      return `<div class="timeline">${blocks}</div>`;
    }

    _renderDetails(attrs) {
      return `
        <div class="details-grid">
          ${this._renderCoveragePanel(attrs)}
        </div>
      `;
    }

    _renderCoveragePanel(attrs) {
      const counts = attrs.counts && typeof attrs.counts === "object" ? attrs.counts : {};

      const coverageKeys = Object.keys(counts)
        .filter((key) => key !== "notes")
        .sort();

      const datasetRows = coverageKeys
        .map((key) => `<li><strong>${esc(DATASET_LABEL[key] || key)}</strong>: ${esc(counts[key])}</li>`)
        .join("");

      return `
        <section class="panel">
          <h4>Operational Details</h4>
          <ul>${datasetRows || "<li>No dataset counts found.</li>"}</ul>
        </section>
      `;
    }

    _renderNotesPanel(attrs) {
      const notes = this._noteEvents(attrs);
      if (!notes.length) {
        return `
          <section class="panel">
            <h4>Notes</h4>
            <div class="meta">No notes found for this trip.</div>
          </section>
        `;
      }

      const rows = notes
        .map((note) => {
          const dt = toDate(note.start) || toDate(note.end) || toDate(note.last_edited_time);
          const dateLabel = dt ? fmtDate(dt) : "Undated";
          const content = String(note.content || note.subtitle || note.location || "").trim();
          const externalUrl = String(note.url || "").trim();
          const detailsUrl = String(note.notion_url || "").trim();
          return `
            <li class="note-item">
              <div class="note-title">${esc(note.title || "Untitled note")}</div>
              ${content ? `<div class="note-sub">${esc(content)}</div>` : ""}
              <div class="note-meta">${esc(dateLabel)}${externalUrl ? ` • <a class="link" href="${esc(externalUrl)}" target="_blank" rel="noopener noreferrer">Link</a>` : ""}${detailsUrl ? ` • <a class="link" href="${esc(detailsUrl)}" target="_blank" rel="noopener noreferrer">Details</a>` : ""}</div>
            </li>
          `;
        })
        .join("");

      return `
        <section class="panel">
          <h4>Notes</h4>
          <ul class="notes-list">${rows}</ul>
        </section>
      `;
    }

    _renderOverview(stateObj, attrs) {
      return `
        <div class="overview-grid">
          <div class="overview-left">
            ${this._renderHero(stateObj, attrs)}
            ${this._renderCoveragePanel(attrs)}
            ${this._renderNotesPanel(attrs)}
          </div>
          <div class="overview-right">
            ${this._renderTimeline(attrs)}
          </div>
        </div>
      `;
    }

    _render() {
      try {
        if (!this._root || !this._config) {
          return;
        }

        const stateObj = this._stateObj();
        if (!stateObj) {
          this._root.innerHTML = `
            <ha-card>
              <div class="wrap">
                <div class="title">Notion Travel</div>
                <div class="empty">Entity ${esc(this._config.entity)} not found.</div>
              </div>
            </ha-card>
          `;
          return;
        }

        const attrs = stateObj.attributes || {};
        const mode = this._config.mode;
        const title = this._config.title || (mode === "overview" ? "Trip Console" : mode === "timeline" ? "Itinerary Timeline" : mode === "details" ? "Trip Details" : "Next Trip");

        let body = "";
        if (mode === "overview") {
          body = this._renderOverview(stateObj, attrs);
        } else if (mode === "timeline") {
          body = this._renderTimeline(attrs);
        } else if (mode === "details") {
          body = this._renderDetails(attrs);
        } else {
          body = this._renderHero(stateObj, attrs);
        }

        this._root.innerHTML = `
          <ha-card>
            <div class="wrap">
              <div class="title">${esc(title)}</div>
              ${body}
            </div>
          </ha-card>
        `;
      } catch (err) {
        this._root.innerHTML = `
          <ha-card>
            <div class="wrap">
              <div class="title">Notion Travel</div>
              <div class="empty">Card render error: ${esc(err && err.message ? err.message : err)}</div>
            </div>
          </ha-card>
        `;
      }
    }
  }

  if (!customElements.get(CARD_TYPE)) {
    customElements.define(CARD_TYPE, NotionTravelTripCard);
  }

  if (!customElements.get(ALIAS_CARD_TYPE)) {
    class NotionTravelTripCardLegacy extends NotionTravelTripCard {}
    customElements.define(ALIAS_CARD_TYPE, NotionTravelTripCardLegacy);
  }

  window.customCards = window.customCards || [];
  window.customCards.push({
    type: CARD_TYPE,
    name: "Notion Travel Trip Card",
    description: "Hero/timeline/details card for Notion Travel itinerary UX.",
  });
  window.customCards.push({
    type: ALIAS_CARD_TYPE,
    name: "Notion Travel Trip Card (Alias)",
    description: "Backward-compatible alias for v2 dashboard references.",
  });
})();
