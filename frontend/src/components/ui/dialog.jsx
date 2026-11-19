import * as React from "react"
import { Dialog as DialogPrimitive, AlertDialog as AlertPrimitive } from "radix-ui"
import { X } from "lucide-react"

import { cn } from "@/lib/utils"

const overlayCls =
  "fixed inset-0 z-50 bg-black/40 backdrop-blur-[2px] data-[state=open]:animate-in data-[state=open]:fade-in-0"
const contentCls =
  "fixed left-1/2 top-1/2 z-50 grid max-h-[92vh] w-[calc(100%-2rem)] -translate-x-1/2 -translate-y-1/2 gap-4 overflow-y-auto rounded-xl border bg-card p-5 text-card-foreground shadow-xl focus:outline-none"

export const Dialog = DialogPrimitive.Root

export function DialogContent({ className, children, ...props }) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className={overlayCls} />
      <DialogPrimitive.Content className={cn(contentCls, "max-w-2xl", className)} {...props}>
        {children}
        <DialogPrimitive.Close
          className="absolute right-3 top-3 rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
          aria-label="Chiudi"
        >
          <X className="size-4" />
        </DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  )
}

export function DialogHeader({ className, ...props }) {
  return <div className={cn("flex flex-col gap-1 pr-6", className)} {...props} />
}

export function DialogTitle({ className, ...props }) {
  return <DialogPrimitive.Title className={cn("text-lg font-semibold", className)} {...props} />
}

export function DialogDescription({ className, ...props }) {
  return <DialogPrimitive.Description className={cn("text-sm text-muted-foreground", className)} {...props} />
}

export function DialogFooter({ className, ...props }) {
  return <div className={cn("flex flex-col-reverse gap-2 sm:flex-row sm:justify-end", className)} {...props} />
}

/** Conferma semplice (usata per la cancellazione). */
export function ConfirmDialog({ open, onOpenChange, title, description, confirmLabel = "Conferma", onConfirm, busy }) {
  return (
    <AlertPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <AlertPrimitive.Portal>
        <AlertPrimitive.Overlay className={overlayCls} />
        <AlertPrimitive.Content className={cn(contentCls, "max-w-md")}>
          <AlertPrimitive.Title className="text-lg font-semibold">{title}</AlertPrimitive.Title>
          <AlertPrimitive.Description className="text-sm text-muted-foreground">
            {description}
          </AlertPrimitive.Description>
          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <AlertPrimitive.Cancel className="h-9 rounded-lg border bg-background px-3 text-sm font-medium hover:bg-muted">
              Annulla
            </AlertPrimitive.Cancel>
            <button
              type="button"
              disabled={busy}
              onClick={onConfirm}
              className="h-9 rounded-lg bg-destructive px-3 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
            >
              {confirmLabel}
            </button>
          </div>
        </AlertPrimitive.Content>
      </AlertPrimitive.Portal>
    </AlertPrimitive.Root>
  )
}
