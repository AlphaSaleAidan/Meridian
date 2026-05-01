/**shadcn/ui Button — New York style, Meridian dark theme.**/
import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

type Variant = 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link'
type Size = 'default' | 'sm' | 'lg' | 'icon'

const variantClasses: Record<Variant, string> = {
  default: 'bg-[#1A8FD6] text-white hover:bg-[#1A8FD6]/90 shadow-sm',
  destructive: 'bg-red-500 text-white hover:bg-red-500/90 shadow-sm',
  outline: 'border border-[#1F1F23] bg-transparent text-[#F5F5F7] hover:bg-[#1F1F23]/60',
  secondary: 'bg-[#1F1F23] text-[#F5F5F7] hover:bg-[#1F1F23]/80',
  ghost: 'text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#1F1F23]/60',
  link: 'text-[#1A8FD6] underline-offset-4 hover:underline',
}

const sizeClasses: Record<Size, string> = {
  default: 'h-10 px-4 py-2 min-h-[44px] sm:min-h-0',
  sm: 'h-8 px-3 text-xs min-h-[44px] sm:min-h-0',
  lg: 'h-12 px-6 text-base',
  icon: 'h-10 w-10 min-h-[44px] min-w-[44px] sm:min-h-0 sm:min-w-0',
}

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1A8FD6]/50 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0A0A0B] disabled:pointer-events-none disabled:opacity-50',
        variantClasses[variant],
        sizeClasses[size],
        className,
      )}
      {...props}
    />
  ),
)
Button.displayName = 'Button'

export { Button }
