"""Fixed reference data shared by validation and the /projects/options endpoint."""

# Projects are filtered and charted by state, so the name must be spelled one way only.
INDIAN_STATES_AND_UNION_TERRITORIES: tuple[str, ...] = (
    # States
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chhattisgarh",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
    # Union territories
    "Andaman and Nicobar Islands",
    "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi",
    "Jammu and Kashmir",
    "Ladakh",
    "Lakshadweep",
    "Puducherry",
)

_STATE_BY_LOWERCASE = {state.lower(): state for state in INDIAN_STATES_AND_UNION_TERRITORIES}


def canonical_state_name(value: str) -> str | None:
    """Return the official spelling for a state typed in any letter case, or None if unknown."""
    return _STATE_BY_LOWERCASE.get(value.strip().lower())
