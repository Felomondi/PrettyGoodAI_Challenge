document.addEventListener("DOMContentLoaded", (): void => {
  const phoneInput = document.getElementById("phone") as HTMLInputElement | null;
  const phoneError = document.getElementById("phone-error") as HTMLElement | null;
  const form = document.getElementById("register-form") as HTMLFormElement | null;

  if (!phoneInput || !phoneError || !form) return;

  // Auto-format to E.164 on blur: strip non-digits, prepend +1 if 10 digits
  phoneInput.addEventListener("blur", (): void => {
    const digits: string = phoneInput.value.replace(/\D/g, "");
    if (digits.length === 10) {
      phoneInput.value = `+1${digits}`;
    } else if (digits.length === 11 && digits.startsWith("1")) {
      phoneInput.value = `+${digits}`;
    }
  });

  // Client-side validation before submit
  form.addEventListener("submit", (e: Event): void => {
    const phone: string = phoneInput.value.trim();
    const isValid: boolean = /^\+1\d{10}$/.test(phone);

    if (!isValid) {
      e.preventDefault();
      phoneError.textContent = "Phone must be in E.164 format: +1XXXXXXXXXX";
      phoneError.style.display = "block";
      phoneInput.focus();
    } else {
      phoneError.style.display = "none";
    }
  });

  // Clear error as user types
  phoneInput.addEventListener("input", (): void => {
    phoneError.style.display = "none";
  });
});
