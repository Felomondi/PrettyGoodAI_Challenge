"use strict";
document.addEventListener("DOMContentLoaded", () => {
    const phoneInput = document.getElementById("phone");
    const phoneError = document.getElementById("phone-error");
    const form = document.getElementById("register-form");
    if (!phoneInput || !phoneError || !form)
        return;
    phoneInput.addEventListener("blur", () => {
        const digits = phoneInput.value.replace(/\D/g, "");
        if (digits.length === 10) {
            phoneInput.value = `+1${digits}`;
        }
        else if (digits.length === 11 && digits.startsWith("1")) {
            phoneInput.value = `+${digits}`;
        }
    });
    form.addEventListener("submit", (e) => {
        const phone = phoneInput.value.trim();
        const isValid = /^\+1\d{10}$/.test(phone);
        if (!isValid) {
            e.preventDefault();
            phoneError.textContent = "Phone must be in E.164 format: +1XXXXXXXXXX";
            phoneError.style.display = "block";
            phoneInput.focus();
        }
        else {
            phoneError.style.display = "none";
        }
    });
    phoneInput.addEventListener("input", () => {
        phoneError.style.display = "none";
    });
});
