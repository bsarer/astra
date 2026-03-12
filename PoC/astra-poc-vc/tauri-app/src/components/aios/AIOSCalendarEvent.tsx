import React from "react";

interface CalendarEventProps {
  time?: string;
  title?: string;
  location?: string;
  attendees?: string[];
}

export function AIOSCalendarEvent({ time = "", title = "", location = "", attendees = [] }: CalendarEventProps) {
  return (
    <div className="aios-calendar-event">
      <div className="cal-time">{time}</div>
      <div>
        <div className="cal-title">{title}</div>
        {location && <div className="cal-location">📍 {location}</div>}
        {attendees.length > 0 && (
          <div className="cal-location">👥 {attendees.join(", ")}</div>
        )}
      </div>
    </div>
  );
}
