(function () {
	
	var CronDerper = function () {
		this.TEMPLATES = {
			YEARLY: "0 {minute} {hour} {day} {month} ?",
			MONTHLY: "0 {minute} {hour} {day} * ?",
			WEEKLY: "0 {minute} {hour} ? * {weekday}",
			DAILY: "0 {minute} {hour} * * ?",
			HOUR_INTERVAL: "0 0 0/{hour} * * ?",
			MINUTE_INTERVAL: "0 0/{minute} * * * ?",
			ADVANCED: "{advanced}"
		};
		
		this.formatString = function(s, vars) {
			var outString = s;
			for (var k in vars) {
				outString = outString.replace("{" + k + "}", vars[k]);
			}
			return outString;
		};
		
		this.VIEWS = {
			YEARLY: "On {month} {day}, at {hour}:{minute}",
			MONTHLY: "On the {day} of every month, at {hour}:{minute}",
			WEEKLY: "Every {weekday}, at {hour}:{minute}",
			DAILY: "Daily, at {hour}:{minute}",
			HOUR_INTERVAL: "Every {hour} hours",
			MINUTE_INTERVAL: "Every {minute} minutes",
			ADVANCED: "Cron expression: {advanced}"
		};
		
		this.FIELDS = {
			minute: "<input class=\"smallInput\" type=\"number\" id=\"minute\" value=\"0\" min=\"0\" max=\"59\" size=\"2\"/>",
			hour: "<input class=\"smallInput\" type=\"number\" id=\"hour\" value=\"0\" min=\"0\" max=\"23\" />",
			day: "<input class=\"smallInput\" type=\"number\" id=\"day\" value=\"0\" min=\"1\" max=\"31\" />",
			weekday: "<select id=\"weekday\"><option value=\"0\">Sunday</option><option value=\"1\">Monday</option><option value=\"2\">Tuesday</option><option value=\"3\">Wednesday</option><option value=\"4\">Thursday</option><option value=\"5\">Friday</option><option value=\"6\">Saturday</option></select>",
			month: "<select id=\"month\"><option value=\"1\">January</option><option value=\"2\">February</option><option value=\"3\">March</option><option value=\"4\">April</option><option value=\"5\">May</option><option value=\"6\">June</option><option value=\"7\">July</option><option value=\"8\">August</option><option value=\"9\">September</option><option value=\"10\">October</option><option value=\"11\">Movember</option><option value=\"12\">Decembeard</option></select>",
			advanced: "<input type=\"text\" id=\"advanced\" value=\"0 0 0/1 * * ?\" />"
		};
		
		this.populateDiv = function (view) {
			document.getElementById("cronInput").innerHTML = this.formatString(this.VIEWS[view], this.FIELDS);
		};
		
		this.generateOutput = function () {
			var fieldValues = {};
			for (var k in this.FIELDS) {
				var field = document.getElementById(k);
				if (field) {
					fieldValues[k] = field.value;
				}
			}
			var template = document.getElementById("cronViewSelection").value;
			document.getElementById("cronOutput").value = this.formatString(this.TEMPLATES[template], fieldValues);
		};
	};
	
	window.CronDerper = CronDerper;
}());
