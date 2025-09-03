"use client"

import * as React from "react"
import Link from "next/link"
import { cn } from "@/lib/utils"

export function Pagination({ className, ...props }: React.ComponentProps<"nav">) {
    return (
        <nav
            role="navigation"
            aria-label="pagination"
            className={cn("mx-auto flex w-full justify-center", className)}
            {...props}
        />
    )
}

export function PaginationContent({ className, ...props }: React.ComponentProps<"ul">) {
    return (
        <ul
            className={cn(
                "flex flex-row items-center gap-1 text-sm text-foreground",
                className
            )}
            {...props}
        />
    )
}

export function PaginationItem({ className, ...props }: React.ComponentProps<"li">) {
    return <li className={cn("", className)} {...props} />
}

type PaginationLinkProps = React.ComponentProps<typeof Link> & {
    isActive?: boolean
}

export function PaginationLink({ className, isActive, ...props }: PaginationLinkProps) {
    return (
        <PaginationItem>
            <Link
                className={cn(
                    "inline-flex h-9 min-w-9 items-center justify-center rounded-md border border-border bg-card px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-secondary",
                    isActive && "border-primary text-primary",
                    className
                )}
                {...props}
            />
        </PaginationItem>
    )
}

export function PaginationPrevious({ className, ...props }: PaginationLinkProps) {
    return (
        <PaginationLink
            aria-label="Go to previous page"
            className={cn("px-2", className)}
            {...props}
        >
            Previous
        </PaginationLink>
    )
}

export function PaginationNext({ className, ...props }: PaginationLinkProps) {
    return (
        <PaginationLink aria-label="Go to next page" className={cn("px-2", className)} {...props}>
            Next
        </PaginationLink>
    )
}

export function PaginationEllipsis({ className, ...props }: React.ComponentProps<"span">) {
    return (
        <span
            aria-hidden
            className={cn(
                "inline-flex h-9 min-w-9 items-center justify-center rounded-md border border-transparent px-3 py-2 text-sm text-muted-foreground",
                className
            )}
            {...props}
        >
            …
        </span>
    )
}


