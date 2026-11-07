"""Official legislature homes for the 50 states in the site's jurisdiction list.

District of Columbia is not a `jur-*` government in this site's Federal/State
control, so it is not part of this feed.
"""

# postal, name, official legislature URL, direct adapter id or None
STATES = [
    ("AL", "Alabama", "https://alison.legislature.state.al.us/", None),
    ("AK", "Alaska", "https://www.akleg.gov/", "ak-basis"),
    ("AZ", "Arizona", "https://www.azleg.gov/", None),
    ("AR", "Arkansas", "https://www.arkleg.state.ar.us/", None),
    ("CA", "California", "https://leginfo.legislature.ca.gov/", None),
    ("CO", "Colorado", "https://leg.colorado.gov/", None),
    ("CT", "Connecticut", "https://www.cga.ct.gov/", None),
    ("DE", "Delaware", "https://legis.delaware.gov/", None),
    ("FL", "Florida", "https://www.flsenate.gov/", None),
    ("GA", "Georgia", "https://www.legis.ga.gov/", None),
    ("HI", "Hawaii", "https://www.capitol.hawaii.gov/", None),
    ("ID", "Idaho", "https://legislature.idaho.gov/", None),
    ("IL", "Illinois", "https://www.ilga.gov/", None),
    ("IN", "Indiana", "https://iga.in.gov/", None),
    ("IA", "Iowa", "https://www.legis.iowa.gov/", None),
    ("KS", "Kansas", "https://www.kslegislature.gov/", None),
    ("KY", "Kentucky", "https://legislature.ky.gov/", None),
    ("LA", "Louisiana", "https://www.legis.la.gov/", None),
    ("ME", "Maine", "https://legislature.maine.gov/", None),
    ("MD", "Maryland", "https://mgaleg.maryland.gov/", None),
    ("MA", "Massachusetts", "https://malegislature.gov/", "ma-acts"),
    ("MI", "Michigan", "https://www.legislature.mi.gov/", None),
    ("MN", "Minnesota", "https://www.revisor.mn.gov/", "mn-session-laws"),
    ("MS", "Mississippi", "https://billstatus.ls.state.ms.us/", None),
    ("MO", "Missouri", "https://house.mo.gov/", None),
    ("MT", "Montana", "https://www.legmt.gov/", None),
    ("NE", "Nebraska", "https://nebraskalegislature.gov/", None),
    ("NV", "Nevada", "https://www.leg.state.nv.us/", None),
    ("NH", "New Hampshire", "https://www.gencourt.state.nh.us/", None),
    ("NJ", "New Jersey", "https://www.njleg.state.nj.us/", None),
    ("NM", "New Mexico", "https://www.nmlegis.gov/", None),
    ("NY", "New York", "https://www.nysenate.gov/legislation", None),
    ("NC", "North Carolina", "https://www.ncleg.gov/", None),
    ("ND", "North Dakota", "https://ndlegis.gov/", None),
    ("OH", "Ohio", "https://www.legislature.ohio.gov/", None),
    ("OK", "Oklahoma", "https://www.oklegislature.gov/", None),
    ("OR", "Oregon", "https://www.oregonlegislature.gov/", "or-odata"),
    ("PA", "Pennsylvania", "https://www.legis.state.pa.us/", None),
    ("RI", "Rhode Island", "https://www.rilegislature.gov/", None),
    ("SC", "South Carolina", "https://www.scstatehouse.gov/", None),
    ("SD", "South Dakota", "https://sdlegislature.gov/", None),
    ("TN", "Tennessee", "https://www.capitol.tn.gov/", None),
    ("TX", "Texas", "https://capitol.texas.gov/", "tx-signed"),
    ("UT", "Utah", "https://le.utah.gov/", None),
    ("VT", "Vermont", "https://legislature.vermont.gov/", None),
    ("VA", "Virginia", "https://lis.virginia.gov/", None),
    ("WA", "Washington", "https://leg.wa.gov/", "wa-signed"),
    ("WV", "West Virginia", "https://www.wvlegislature.gov/", None),
    ("WI", "Wisconsin", "https://docs.legis.wisconsin.gov/", "wi-acts"),
    ("WY", "Wyoming", "https://www.wyoleg.gov/", "wy-bills"),
]

BY_CODE = {code: {"code": code, "name": name, "officialUrl": url, "adapter": adapter} for code, name, url, adapter in STATES}

UNCONFIGURED_NOTE = (
    "No direct enacted-bill parser is configured for this state yet. "
    "The scheduled ingest uses the Open States API for this state when the "
    "OPENSTATES_API_KEY repository secret is set, and cites each bill's official "
    "source URL from that record. Nothing is invented when the source is unavailable."
)
