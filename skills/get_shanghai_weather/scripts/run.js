function normalizeAmpm(value) {
  const v = String(value || '').trim().toLowerCase();
  if (['am', 'a', 'morning', '上午'].includes(v)) return 'am';
  if (['pm', 'p', 'afternoon', '下午'].includes(v)) return 'pm';
  return v;
}

function todayLocalIsoDate() {
  const now = new Date();
  const offsetMs = now.getTimezoneOffset() * 60 * 1000;
  return new Date(now.getTime() - offsetMs).toISOString().slice(0, 10);
}

function main(params) {
  params = params && typeof params === 'object' && !Array.isArray(params) ? params : {};

  let dateStr = String(params.date || '').trim();
  const ampmRaw = String(params.ampm || '').trim();

  if (!dateStr) dateStr = todayLocalIsoDate();

  if (dateStr.length !== 10 || dateStr[4] !== '-' || dateStr[7] !== '-') {
    return {
      success: false,
      error: 'Invalid date format. Expected YYYY-MM-DD',
      received: { date: dateStr, ampm: ampmRaw },
    };
  }

  const ampm = normalizeAmpm(ampmRaw) || 'am';
  if (!['am', 'pm'].includes(ampm)) {
    return {
      success: false,
      error: 'Invalid ampm value. Use am/pm (or morning/afternoon, 上午/下午)',
      received: { date: dateStr, ampm: ampmRaw },
    };
  }

  // Demo output (replace with real API call later)
  return {
    success: true,
    data: {
      city: 'Guangzhou',
      date: dateStr,
      ampm,
      weather: 'sunny',
      temperature_c: ampm === 'am' ? 24 : 29,
    },
  };
}

let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => {
  input += chunk;
});
process.stdin.on('end', () => {
  let params = {};
  try {
    params = JSON.parse(input || '{}');
  } catch (e) {
    params = {};
  }

  const result = main(params);
  process.stdout.write(JSON.stringify(result));
});

if (process.stdin.isTTY) {
  // If executed without stdin piping, still run with empty params.
  const result = main({});
  process.stdout.write(JSON.stringify(result));
}
