#!/usr/bin/env python3
"""Hand-entered starter listings so the site isn't empty on day one.

Every org here is real and currently takes high-school-age volunteers in
one of the nine cities within about 15 miles of Fremont. Treat this as a bootstrap: once the
scrapers run, real listings merge in alongside these. Descriptions are
written by us, not copied.

Two things to keep in mind when you add a row:

  * `min_age` is what the source actually publishes. Several of these orgs
    don't post an age floor at all -- those stay None and land in the site's
    "age isn't posted" group, with a phone number in the description so a
    student can just ask.
  * Set `min_age` explicitly whenever the description mentions any other
    number of years. `normalize.parse_min_age()` would happily read "camps
    for ages 5 to 12" as a minimum age of 5; an explicit value blocks it.

    python seed.py
"""

import datetime as dt
from pathlib import Path

from pipeline.geocode import assign_coordinates
from pipeline.models import Opportunity
from pipeline.normalize import enrich
from pipeline.store import Store

SEED = [
    dict(
        title="Historic garden upkeep, first Saturday of the month",
        org="California Nursery Historical Park",
        url="https://www.fremont.gov/residents/volunteer",
        min_age=14,
        city="Fremont",
        address="36501 Niles Blvd, Fremont, CA",
        weekend=True,
        commitment="recurring",
        causes=["environment", "community"],
        description=(
            "Weeding, mulching and raking in the rose, shade and succulent "
            "gardens. Tools and training provided; 9am to noon, stay for as "
            "much as you want. Wear closed-toe shoes and bring water."
        ),
    ),
    dict(
        title="Teen library volunteer",
        org="Fremont Main Library",
        url="https://fremont.libnet.info/volunteer",
        min_age=13,
        city="Fremont",
        address="2400 Stevenson Blvd, Fremont, CA",
        commitment="recurring",
        causes=["education", "community"],
        signs_hours=True,
        description=(
            "Roughly one two-hour shift a week. Shelving, program setup and "
            "help at events. Some assignments need a background check."
        ),
    ),
    dict(
        title="Clerical support for the library foundation",
        org="Alameda County Library Foundation",
        url="https://fremont.libnet.info/volunteer",
        min_age=14,
        city="Fremont",
        address="2450 Stevenson Blvd, Fremont, CA",
        weekday=True,
        commitment="recurring",
        causes=["community", "education"],
        description=(
            "Filing, mailing prep and light data entry, about 1.5 to 3 hours "
            "a week between Monday and Thursday, typically 3:30 to 5pm. Runs "
            "year round."
        ),
    ),
    dict(
        title="Food distribution helper",
        org="Tri-City Volunteers",
        url="https://www.tricityvolunteers.org/",
        min_age=14,
        city="Fremont",
        causes=["food", "community"],
        signs_hours=True,
        description=(
            "One of the largest food distributors in Alameda County. During "
            "school breaks, high-school-age volunteers can drop in on a "
            "first-come basis to help with distribution and the thrift store."
        ),
    ),
    dict(
        title="Hospital volunteer program",
        org="Washington Hospital",
        url="https://www.whhs.com/",
        min_age=16,
        city="Fremont",
        causes=["health"],
        commitment="recurring",
        signs_hours=True,
        description=(
            "Year-round placements for students 16 and up in good academic "
            "standing, including the gift shop and patient-facing roles. "
            "Requires an application and a time commitment."
        ),
    ),
    dict(
        title="Tree planting and care days",
        org="Urban Forest Friends",
        url="https://www.urbanforestfriends.org/home",
        min_age=None,
        city="Fremont",
        weekend=True,
        commitment="one_time",
        causes=["environment"],
        description=(
            "Planting and maintaining trees around Fremont. Event-based, "
            "signup through their site. Age policy is not posted — ask when "
            "you sign up."
        ),
    ),
    dict(
        title="Afterschool program tutor",
        org="American Chinese School",
        url="https://www.idealist.org/",
        min_age=14,
        city="Fremont",
        address="36060 Fremont Blvd, Fremont, CA",
        weekday=True,
        commitment="recurring",
        causes=["education", "youth"],
        signs_hours=True,
        description=(
            "Help elementary students with homework and STEAM activities, "
            "supervise outdoor time and assist teachers. Training provided "
            "and they explicitly welcome students working on service hours."
        ),
    ),
    dict(
        title="Community Circle for children with special needs",
        org="Bountiful Blossom",
        url="https://web.bountifulblossom.org/volunteer-opportunities/youth-volunteer-opportunities/",
        min_age=14,
        city="Fremont",
        weekend=True,
        commitment="one_time",
        causes=["youth", "community"],
        description=(
            "Event-based sessions at the Fremont Main Library supporting "
            "children with special needs. They recruit high-school "
            "volunteers for each session."
        ),
    ),
    dict(
        title="Youth office volunteer",
        org="SAVE (Safe Alternatives to Violent Environments)",
        url="https://save-dv.org/",
        min_age=14,
        city="Fremont",
        commitment="recurring",
        causes=["community"],
        description=(
            "Office support at the Fremont location. Most direct-service "
            "roles are adults-only, but there are youth placements."
        ),
    ),
    dict(
        title="Coastal Cleanup Day",
        org="City of Fremont Environmental Services",
        url="https://www.fremont.gov/residents/volunteer",
        min_age=None,
        city="Fremont",
        weekend=True,
        commitment="one_time",
        causes=["environment", "community"],
        signs_hours=True,
        description=(
            "Annual all-ages cleanup run through the city. Also worth "
            "checking their Adopt-A-Drain program for something ongoing."
        ),
    ),

    # --- San Jose -----------------------------------------------------
    dict(
        title="Teens Reach library volunteer",
        org="San José Public Library",
        url="https://www.sjpl.org/teensreach/",
        min_age=13,
        max_age=18,
        city="San Jose",
        commitment="recurring",
        causes=["education", "community", "youth"],
        signs_hours=True,
        description=(
            "Teens support library programs and events — children's craft "
            "programs, the summer learning registration table, community "
            "outreach — and serve as library advisors. Members earn "
            "community service hours. Each branch signs up separately."
        ),
    ),
    dict(
        title="Food sorting at the Curtner and Cypress centers",
        org="Second Harvest of Silicon Valley",
        url="https://www.shfb.org/give-help/volunteer/individual-volunteering/",
        min_age=12,
        city="San Jose",
        causes=["food", "community"],
        # Explicitly False, not None: they state a policy, and it's "no".
        signs_hours=False,
        description=(
            "Sorting and packing produce and dry goods at two San Jose "
            "warehouses. The floor is 12, but 12-to-15s need one adult per "
            "five youths, so in practice you can only sign up alone at 16. "
            "They don't sign third-party hour forms — print a timecard each "
            "shift and your history stays on your account."
        ),
    ),
    dict(
        title="One-day park volunteer events",
        org="City of San José Parks, Recreation & Neighborhood Services",
        url=(
            "https://www.sanjoseca.gov/your-government/departments-offices/"
            "parks-recreation-neighborhood-services/get-involved/volunteer-with-us"
        ),
        min_age=None,
        city="San Jose",
        commitment="one_time",
        causes=["environment", "community"],
        signs_hours=True,
        description=(
            "Park cleanup and beautification events, usually 8:45am to noon "
            "with supplies provided, posted on the city's volunteer "
            "calendar. The city verifies community service hours. No age "
            "floor is published — email ParkVolunteer@sanjoseca.gov to ask."
        ),
    ),

    # --- Newark -------------------------------------------------------
    dict(
        title="Teen summer program leader",
        org="League of Volunteers",
        url="https://www.lov.org/",
        # Set explicitly: the description mentions elementary-age campers,
        # and the age parser must not pick that up as the floor.
        min_age=13,
        max_age=17,
        city="Newark",
        commitment="recurring",
        causes=["youth", "community"],
        description=(
            "LOV is the Tri-City volunteer clearinghouse for Fremont, Newark "
            "and Union City. Teen volunteers help lead activities and assist "
            "staff at the summer recreation camps for elementary-age kids, "
            "which is real leadership experience. Under 18 needs parental "
            "consent. Office is open weekdays 8am to 5pm."
        ),
    ),
    dict(
        title="Community Thanksgiving dinner and holiday drives",
        org="League of Volunteers",
        url="https://www.lov.org/",
        min_age=None,
        city="Newark",
        commitment="one_time",
        causes=["food", "community", "seniors"],
        description=(
            "LOV has run a free community Thanksgiving dinner for close to "
            "four decades, alongside holiday food and toy drives and an "
            "Adopt-A-Family program. Volunteers under 18 need parental "
            "consent; no age floor is posted for the dinner itself. Call "
            "(510) 793-5683."
        ),
    ),
    dict(
        title="Sorting food and clothing at the center",
        org="Viola Blythe Community Services",
        url="https://www.violablythe.org/volunteer",
        min_age=None,
        city="Newark",
        address="37365 Ash St, Newark, CA",
        causes=["food", "community", "youth"],
        description=(
            "Processing requests, sorting food and clothing and stocking "
            "shelves at the Ash Street center, plus seasonal toy collection "
            "and the children's Christmas party. No age policy is posted — "
            "call (510) 794-3437 or email violablythectr@gmail.com to ask."
        ),
    ),
    dict(
        title="Police department community volunteer (R.A.V.E.N.)",
        org="Newark Police Department",
        url=(
            "https://www.newarkca.gov/departments/police/"
            "get-involved-community-engagement/r-a-v-e-n-volunteer-program"
        ),
        min_age=None,
        city="Newark",
        causes=["community"],
        description=(
            "R.A.V.E.N. places community volunteers with the police "
            "department, explicitly including high school students weighing "
            "a career in law enforcement. Ask the community engagement "
            "manager at 510-578-4929 about current openings."
        ),
    ),

    # --- Union City ---------------------------------------------------
    dict(
        title="Thrift shop and Wednesday produce distribution",
        org="Centro de Servicios",
        url="https://centrouc.org/",
        min_age=None,
        city="Union City",
        address="525 H St, Union City, CA",
        weekday=True,
        commitment="recurring",
        causes=["food", "community"],
        description=(
            "Centro asks for youth volunteers at its community thrift store "
            "on H Street and at the Wednesday morning produce hand-out. "
            "Groceries go out the last Thursday of each month. No age floor "
            "is posted — call 510-489-4100."
        ),
    ),
    dict(
        title="Recreation and special event volunteer",
        org="Union City Community & Recreation Services",
        url="https://www.unioncityca.gov/808/Volunteer-Opportunities",
        min_age=None,
        city="Union City",
        address="34009 Alvarado-Niles Rd, Union City, CA",
        causes=["community", "environment", "seniors"],
        description=(
            "The city lists special event help, park maintenance, Ruggieri "
            "Center senior support and art teaching. Nothing about age "
            "appears online — call Community & Recreation Services at "
            "510-471-3232 and ask which roles take students."
        ),
    ),
    dict(
        title="Elementary homework assistant at Kennedy Youth Center",
        org="Union City Community & Recreation Services",
        url="https://www.unioncityca.gov/288/Kennedy-Youth-Center",
        min_age=None,
        city="Union City",
        address="1333 Decoto Rd, Union City, CA",
        weekday=True,
        commitment="recurring",
        causes=["education", "youth"],
        description=(
            "Help elementary students with homework at the Kennedy Youth "
            "Center on Decoto Road. The center runs drop-in Monday, "
            "Tuesday, Thursday and Friday afternoons and opens earlier on "
            "Wednesday. No age floor is posted — call 510.675.5329."
        ),
    ),

    # --- Milpitas -----------------------------------------------------
    dict(
        title="Remote student volunteering for shelter animals",
        org="Humane Society Silicon Valley",
        url="https://www.hssv.org/volunteer/student-opportunities/",
        # Left None on purpose: the remote roles publish no floor. The
        # description avoids the words "18 and older" and "adults only"
        # because parse_min_age() would read either as a floor of 18 and
        # wrongly hide this from the students it's actually for.
        min_age=None,
        city="Milpitas",
        address="901 Ames Ave, Milpitas, CA",
        remote=True,
        causes=["animals"],
        signs_hours=True,
        description=(
            "Onsite shifts are for adult volunteers, but students can still "
            "help from home: foster a pet with a parent or guardian, or sew "
            "no-sew fleece blankets for shelter animals, which earns half an "
            "hour of credit each. Email volunteer@hssv.org for a letter "
            "verifying your hours."
        ),
    ),

    # --- Hayward ------------------------------------------------------
    dict(
        title="Children's room helper",
        org="Hayward Public Library",
        url="https://www.hayward-ca.gov/public-library/get-involved/volunteer-opportunities-teens",
        min_age=12,          # stated as 7th grade
        max_age=18,          # stated as 12th grade
        city="Hayward",
        address="888 C St, Hayward, CA",
        causes=["education", "youth", "community"],
        description=(
            "Work alongside librarians in the children's section — cleaning "
            "books, prepping crafts and helping where needed. Open to grades "
            "7 through 12, in one-hour shifts you schedule yourself. "
            "Applications open during the school year; ask "
            "hpl.teens@hayward-ca.gov."
        ),
    ),
    dict(
        title="Animal care and docent volunteer",
        org="Sulphur Creek Nature Center",
        url="https://www.haywardrec.org/183/Volunteer",
        min_age=13,
        city="Hayward",
        address="1801 D St, Hayward, CA",
        commitment="recurring",
        causes=["animals", "environment", "education"],
        description=(
            "Animal care, docent work, gardening and summer wildlife camp "
            "counseling at the rec district's nature center. Open from 13 up, "
            "but they ask for a real commitment: one 2-to-4-hour shift a "
            "week for a year, plus a TB test. nature@haywardrec.org."
        ),
    ),

    # --- Castro Valley ------------------------------------------------
    dict(
        title="Volunteer shelving at Castro Valley Library",
        org="Castro Valley Library",
        url="https://aclibrary.org/teens/",
        # No number is published -- the posting says "high school students
        # only", which normalize.enrich() maps to 14 via _AGE_HINTS.
        min_age=None,
        city="Castro Valley",
        commitment="recurring",
        causes=["education", "community"],
        description=(
            "Shelving, tidying, cleaning materials and helping run library "
            "programs. Posted for high school students only. Shifts run 4pm "
            "to 6pm, two hours at a time, up to twice a week and ten hours a "
            "quarter. Training on your first day. Sign up through Alameda "
            "County Library's Better Impact page."
        ),
    ),

    # --- Dublin -------------------------------------------------------
    dict(
        title="Law Enforcement Youth Academy",
        org="Dublin Police Services",
        url="https://www.dublin.ca.gov/1402/Volunteer-Opportunities",
        min_age=14,
        max_age=18,
        city="Dublin",
        commitment="one_time",
        causes=["community", "education"],
        description=(
            "A week-long summer session for high school students weighing a "
            "career in criminal justice. Runs as a single cohort rather than "
            "ongoing shifts. Email Catalina.Medeles@dublin.ca.gov about the "
            "next one."
        ),
    ),
    dict(
        title="Community programs and projects volunteer",
        org="City of Dublin Parks & Community Services",
        url="https://www.dublin.ca.gov/1402/Volunteer-Opportunities",
        min_age=None,
        city="Dublin",
        causes=["community", "youth"],
        description=(
            "The city takes individual and group volunteers for community "
            "programs and projects, including the Jr. Golden State "
            "basketball league. Read the Volunteer Program Guide first, then "
            "apply through the city's job portal. No age floor is posted — "
            "email recreation@dublin.ca.gov."
        ),
    ),

    # --- Pleasanton ---------------------------------------------------
    dict(
        title="Cat, dog and treatment room care",
        org="Valley Humane Society",
        url="https://www.valleyhumane.org/volunteer/",
        min_age=16,
        city="Pleasanton",
        address="3670 Nevada St, Pleasanton, CA",
        commitment="recurring",
        causes=["animals"],
        description=(
            "Cat care, dog care and treatment room support at the Nevada "
            "Street adoption center. Animal care starts at 16; AniMeals and "
            "customer service are older. They want one set weekly shift and "
            "roughly six months, and they don't take drop-ins."
        ),
    ),
    dict(
        title="Meal service at the senior center",
        org="Open Heart Kitchen",
        url="https://www.openheartkitchen.org/volunteer",
        min_age=16,
        city="Pleasanton",
        address="5353 Sunol Blvd, Pleasanton, CA",
        weekday=True,
        weekend=False,      # stated: Sat/Sun shifts are 18+ only
        commitment="recurring",
        causes=["food", "seniors", "community"],
        description=(
            "The Tri-Valley's hot meal program. Volunteers prep and serve "
            "lunches at the Pleasanton Senior Center, with other sites at the "
            "Dublin Senior Center and in Livermore. The floor is 16 even with "
            "a guardian, and weekend shifts are restricted to grown-ups, so "
            "students volunteer on weekdays. volunteerservices@openheartkitchen.org."
        ),
    ),
]


def main() -> None:
    opps = []
    for row in SEED:
        o = Opportunity(source="seed", **row)
        enrich(o)
        assign_coordinates(o)
        opps.append(o)

    path = Path(__file__).parent / "data" / "opportunities.json"
    store = Store(path)
    report = store.merge(opps, dt.date.today().isoformat(), ["seed"], [])
    store.save()
    print(report.summary())
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
