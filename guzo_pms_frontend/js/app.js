// js/app.js

// === CONFIG ================================================================
const API_BASE = "http://127.0.0.1:8000";
const AUTH_TOKEN = "<REDACTED_DEMO_BEARER_TOKEN>"; // same as React dashboard

// Approximate number of rooms per property
const ROOMS_TOTAL_BY_PROPERTY = {
  DRE001: 60, // Dream Big Hotel
  "N&N002": 45, // N&N Luxury Hotel
};

// Map property_code -> hotel name
const HOTEL_NAME_BY_PROPERTY = {
  DRE001: "Dream Big Hotel",
  "N&N002": "N&N Luxury Hotel",
};

// === DATE HELPERS ==========================================================

function toLocalDate(isoDate) {
  // isoDate is like "2025-11-27"
  const [year, month, day] = isoDate.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function formatShortDate(isoDate) {
  if (!isoDate) return "";
  const d = toLocalDate(isoDate);
  return d.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

function todayIso() {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

// === BOOKING LOGIC =========================================================

function bucketBooking(b, businessDate) {
  const ci = toLocalDate(b.check_in);
  const co = toLocalDate(b.check_out);

  const bd = businessDate;

  const isCancelled =
    b.status === "cancelled" || b.status === "no_show" || b.status === "No Show";

  if (isCancelled) {
    return "cancelled";
  }

  // Departures Today: check_out is the business date
  const sameCheckoutDay =
    co.getFullYear() === bd.getFullYear() &&
    co.getMonth() === bd.getMonth() &&
    co.getDate() === bd.getDate();

  // In-house: check_in <= businessDate < check_out
  const isInHouse = ci <= bd && bd < co;

  // Arrivals Today: check_in is business date
  const sameCheckinDay =
    ci.getFullYear() === bd.getFullYear() &&
    ci.getMonth() === bd.getMonth() &&
    ci.getDate() === bd.getDate();

  if (sameCheckinDay && !isCancelled && !isInHouse && !sameCheckoutDay) {
    return "arrivals";
  }

  if (isInHouse) {
    return "in_house";
  }

  if (sameCheckoutDay && !isCancelled) {
    return "departures";
  }

  // If booking is purely in the future
  if (ci > bd) {
    return "future";
  }

  return "future";
}

function formatCurrency(amount) {
  if (amount == null || isNaN(amount)) return "-";
  return new Intl.NumberFormat("en-ET", {
    style: "currency",
    currency: "ETB",
    maximumFractionDigits: 0,
  }).format(amount);
}

// === DOM HELPERS ===========================================================

function $(selector) {
  return document.querySelector(selector);
}

function clearTbody(tbody) {
  while (tbody.firstChild) {
    tbody.removeChild(tbody.firstChild);
  }
}

function renderEmptyRow(tbody) {
  const tr = document.createElement("tr");
  const td = document.createElement("td");
  td.colSpan = 12;
  td.className = "empty-cell";
  td.textContent = "No bookings in this category.";
  tr.appendChild(td);
  tbody.appendChild(tr);
}

function setError(message) {
  const bar = $("#errorBar");
  if (!message) {
    bar.hidden = true;
    bar.textContent = "";
  } else {
    bar.hidden = false;
    bar.textContent = message;
  }
}

// === API CALLS =============================================================

async function fetchBookingsForDate(businessDateIso) {
  const url = `${API_BASE}/frontdesk/bookings?scope=today&date=${businessDateIso}`;
  const res = await fetch(url, {
    headers: {
      Authorization: `Bearer ${AUTH_TOKEN}`,
    },
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(
      `Error ${res.status} loading bookings: ${text || res.statusText}`
    );
  }

  return res.json();
}

async function assignRoom(bookingId, roomNumber) {
  const url = `${API_BASE}/frontdesk/assign-room`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${AUTH_TOKEN}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ booking_id: bookingId, room_number: roomNumber }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(
      `Error ${res.status} assigning room: ${text || res.statusText}`
    );
  }
}

// === RENDERING =============================================================

function computeHouseCount(inHouseBookings, propertyFilter) {
  // Total rooms: either all properties or a subset
  let totalRooms = 0;
  if (propertyFilter === "ALL") {
    totalRooms = Object.values(ROOMS_TOTAL_BY_PROPERTY).reduce(
      (sum, n) => sum + n,
      0
    );
  } else {
    totalRooms = ROOMS_TOTAL_BY_PROPERTY[propertyFilter] || 0;
  }

  // Occupied rooms: in-house + has room_number
  const occupiedRooms = inHouseBookings.filter((b) => {
    if (propertyFilter !== "ALL" && b.property_code !== propertyFilter) {
      return false;
    }
    return !!b.room_number;
  }).length;

  const vacantRooms = Math.max(totalRooms - occupiedRooms, 0);
  const occupancyPct = totalRooms > 0 ? (occupiedRooms / totalRooms) * 100 : 0;

  return { totalRooms, occupiedRooms, vacantRooms, occupancyPct };
}

function enrichBooking(b) {
  // Add hotel_name from property code
  const hotelName = HOTEL_NAME_BY_PROPERTY[b.property_code] || b.property_code;
  return {
    ...b,
    hotel_name: b.hotel_name || hotelName,
  };
}

function renderBookingRow(b, tbody, businessDateIso) {
  const tr = document.createElement("tr");

  const nights =
    b.nights != null
      ? b.nights
      : (() => {
          try {
            const ci = toLocalDate(b.check_in);
            const co = toLocalDate(b.check_out);
            const diff = (co - ci) / (1000 * 60 * 60 * 24);
            return diff || "";
          } catch {
            return "";
          }
        })();

  const total =
    b.total_amount_etb != null
      ? b.total_amount_etb
      : b.total_price != null
      ? b.total_price
      : null;

  const note = b.note || b.notes || "";

  const columns = [
    b.guest_name || "",
    b.hotel_name || "",
    b.property_code || "",
    b.room_number || "TBD",
    formatShortDate(b.check_in),
    formatShortDate(b.check_out),
    nights || "",
    b.status || "",
    b.channel || "",
    formatCurrency(total),
    note,
  ];

  columns.forEach((value) => {
    const td = document.createElement("td");
    td.textContent = value;
    tr.appendChild(td);
  });

  // Action column
  const tdAction = document.createElement("td");
  const btn = document.createElement("button");
  btn.className = "table-btn table-btn-primary";
  btn.textContent = "Assign Room";
  btn.addEventListener("click", async () => {
    const current = b.room_number || "";
    const input = window.prompt(
      `Assign room for ${b.guest_name} (${b.property_code})`,
      current || "101"
    );
    if (!input) return;

    try {
      await assignRoom(b.id, input.trim());
      // After success, reload the page data
      await loadAndRender(businessDateIso);
    } catch (err) {
      console.error(err);
      setError(err.message);
    }
  });
  tdAction.appendChild(btn);
  tr.appendChild(tdAction);

  tbody.appendChild(tr);
}

function updateKpis(buckets, houseCount) {
  $("#kpiArrivals").textContent = buckets.arrivals.length;
  $("#kpiInHouse").textContent = buckets.in_house.length;
  $("#kpiDepartures").textContent = buckets.departures.length;
  $("#kpiCancelled").textContent = buckets.cancelled.length;
  $("#kpiOccupancy").textContent = `${houseCount.occupancyPct.toFixed(1)}%`;

  $("#hcTotalRooms").textContent = houseCount.totalRooms;
  $("#hcOccupiedRooms").textContent = houseCount.occupiedRooms;
  $("#hcVacantRooms").textContent = houseCount.vacantRooms;
  $("#hcOccupancyPct").textContent = `${houseCount.occupancyPct.toFixed(1)}%`;

  $("#countArrivals").textContent = buckets.arrivals.length;
  $("#countInHouse").textContent = buckets.in_house.length;
  $("#countDepartures").textContent = buckets.departures.length;
  $("#countUpcoming").textContent = buckets.future.length;
  $("#countCancelled").textContent = buckets.cancelled.length;
}

function renderBuckets(allBookings, businessDateIso, propertyFilter) {
  const businessDate = toLocalDate(businessDateIso);

  const filtered =
    propertyFilter === "ALL"
      ? allBookings
      : allBookings.filter((b) => b.property_code === propertyFilter);

  const buckets = {
    arrivals: [],
    in_house: [],
    departures: [],
    future: [],
    cancelled: [],
  };

  filtered.forEach((raw) => {
    const b = enrichBooking(raw);
    const bucket = bucketBooking(b, businessDate);
    if (bucket === "arrivals") buckets.arrivals.push(b);
    else if (bucket === "in_house") buckets.in_house.push(b);
    else if (bucket === "departures") buckets.departures.push(b);
    else if (bucket === "cancelled") buckets.cancelled.push(b);
    else buckets.future.push(b);
  });

  // House count based on in-house bucket, filtered by property
  const hc = computeHouseCount(buckets.in_house, propertyFilter);

  updateKpis(buckets, hc);

  // Render each table
  const tbodyArrivals = $("#tbodyArrivals");
  const tbodyInHouse = $("#tbodyInHouse");
  const tbodyDepartures = $("#tbodyDepartures");
  const tbodyUpcoming = $("#tbodyUpcoming");
  const tbodyCancelled = $("#tbodyCancelled");

  clearTbody(tbodyArrivals);
  clearTbody(tbodyInHouse);
  clearTbody(tbodyDepartures);
  clearTbody(tbodyUpcoming);
  clearTbody(tbodyCancelled);

  if (buckets.arrivals.length === 0) {
    renderEmptyRow(tbodyArrivals);
  } else {
    buckets.arrivals.forEach((b) =>
      renderBookingRow(b, tbodyArrivals, businessDateIso)
    );
  }

  if (buckets.in_house.length === 0) {
    renderEmptyRow(tbodyInHouse);
  } else {
    buckets.in_house.forEach((b) =>
      renderBookingRow(b, tbodyInHouse, businessDateIso)
    );
  }

  if (buckets.departures.length === 0) {
    renderEmptyRow(tbodyDepartures);
  } else {
    buckets.departures.forEach((b) =>
      renderBookingRow(b, tbodyDepartures, businessDateIso)
    );
  }

  if (buckets.future.length === 0) {
    renderEmptyRow(tbodyUpcoming);
  } else {
    buckets.future.forEach((b) =>
      renderBookingRow(b, tbodyUpcoming, businessDateIso)
    );
  }

  if (buckets.cancelled.length === 0) {
    renderEmptyRow(tbodyCancelled);
  } else {
    buckets.cancelled.forEach((b) =>
      renderBookingRow(b, tbodyCancelled, businessDateIso)
    );
  }
}

function populatePropertyFilter(allBookings) {
  const select = $("#propertyFilter");
  // Clear existing except "ALL"
  while (select.options.length > 1) {
    select.remove(1);
  }

  const codes = Array.from(new Set(allBookings.map((b) => b.property_code))).sort();
  codes.forEach((code) => {
    if (!code) return;
    const option = document.createElement("option");
    option.value = code;
    const label =
      HOTEL_NAME_BY_PROPERTY[code] != null
        ? `${HOTEL_NAME_BY_PROPERTY[code]} (${code})`
        : code;
    option.textContent = label;
    select.appendChild(option);
  });
}

// === MAIN LOAD =============================================================

let currentBookings = [];
let currentBusinessDateIso = todayIso();

async function loadAndRender(businessDateIso) {
  setError(null);
  currentBusinessDateIso = businessDateIso;

  $("#businessDateLabel").textContent = `Today: ${formatShortDate(
    businessDateIso
  )}`;
  $("#viewScopeLabel").textContent = "Scope: Today (touches today)";

  const propertyFilter = $("#propertyFilter").value || "ALL";
  $("#propertyLabel").textContent =
    propertyFilter === "ALL"
      ? "Property: All Properties"
      : `Property: ${propertyFilter}`;

  try {
    const bookings = await fetchBookingsForDate(businessDateIso);
    currentBookings = Array.isArray(bookings) ? bookings : [];
    populatePropertyFilter(currentBookings);
    renderBuckets(currentBookings, businessDateIso, propertyFilter);
  } catch (err) {
    console.error(err);
    setError(err.message);
  }
}

// === EVENT BINDINGS ========================================================

document.addEventListener("DOMContentLoaded", () => {
  const dateInput = $("#businessDateInput");
  const refreshBtn = $("#refreshButton");
  const propertySelect = $("#propertyFilter");

  // Initialize date input
  const iso = todayIso();
  dateInput.value = iso;

  refreshBtn.addEventListener("click", () => {
    const value = dateInput.value || todayIso();
    loadAndRender(value);
  });

  propertySelect.addEventListener("change", () => {
    if (!currentBookings || currentBookings.length === 0) return;
    const value = propertySelect.value || "ALL";
    $("#propertyLabel").textContent =
      value === "ALL" ? "Property: All Properties" : `Property: ${value}`;
    renderBuckets(currentBookings, currentBusinessDateIso, value);
  });

  // Initial load
  loadAndRender(iso);
});
