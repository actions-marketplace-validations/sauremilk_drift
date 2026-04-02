"""GCD target: functions with complex logic but no guard clauses."""


def process_registration(name, email, age, referral_code, preferences):
    result = {}
    if name and email:
        if age and age >= 18:
            if "@" in email and "." in email:
                result["name"] = name
                result["email"] = email
                result["age"] = age
                if referral_code:
                    if len(referral_code) == 8:
                        result["referral"] = referral_code
                        if preferences:
                            result["prefs"] = preferences
                        result["status"] = "complete"
                    else:
                        result["status"] = "invalid_referral"
                else:
                    result["status"] = "no_referral"
            else:
                result["status"] = "invalid_email"
        else:
            result["status"] = "underage"
    else:
        result["status"] = "missing_fields"
    return result
