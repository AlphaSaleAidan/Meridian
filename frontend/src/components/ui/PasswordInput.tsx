import { forwardRef, useState, type InputHTMLAttributes } from 'react'
import { Eye, EyeOff } from 'lucide-react'

export type PasswordInputProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'type'>

/**
 * Controlled password input with a show/hide visibility toggle.
 *
 * Passes every standard input prop straight through (value, onChange,
 * placeholder, required, minLength, autoComplete, id, name, ...) and applies
 * the caller's className to the <input> itself, so each page keeps its exact
 * existing field styling. Only `pr-10` is appended so typed text never runs
 * under the eye button.
 */
const PasswordInput = forwardRef<HTMLInputElement, PasswordInputProps>(
  function PasswordInput({ className = '', ...props }, ref) {
    const [visible, setVisible] = useState(false)
    return (
      <div className="relative">
        <input
          ref={ref}
          type={visible ? 'text' : 'password'}
          className={`${className} pr-10`}
          {...props}
        />
        <button
          type="button"
          onClick={() => setVisible(v => !v)}
          aria-label={visible ? 'Hide password' : 'Show password'}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-[#A1A1A8]/60 hover:text-[#F5F5F7] transition-colors"
        >
          {visible ? <EyeOff size={16} /> : <Eye size={16} />}
        </button>
      </div>
    )
  }
)

export default PasswordInput
