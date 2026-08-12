export function isArabic(text: string) {
  const ar = (text.match(/[\u0600-\u06FF]/g) || []).length;
  const en = (text.match(/[A-Za-z]/g) || []).length;
  return ar > en;
}
