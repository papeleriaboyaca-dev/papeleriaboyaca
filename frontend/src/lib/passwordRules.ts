import { z } from "zod";

export const PASSWORD_MESSAGE =
  "Mínimo 8 caracteres, una mayúscula, una minúscula, un número y un carácter especial";

const _PASSWORD_RE =
  /^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*()\-_=+[\]{}|\\:;"'<>,.?/~`]).{8,72}$/;

export const passwordSchema = z
  .string()
  .min(8, PASSWORD_MESSAGE)
  .max(72, "Máximo 72 caracteres")
  .refine((v) => _PASSWORD_RE.test(v), PASSWORD_MESSAGE);
