"use client";

import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from "@tanstack/react-table";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";
import type { DealRow } from "@/lib/queries";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const brl = (v: number | null) =>
  v == null
    ? "—"
    : v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

const columns: ColumnDef<DealRow>[] = [
  {
    accessorKey: "title",
    header: "Produto",
    cell: ({ getValue }) => (
      <span className="block max-w-md truncate" title={String(getValue())}>
        {String(getValue())}
      </span>
    ),
  },
  {
    accessorKey: "store",
    header: "Loja",
    cell: ({ getValue }) => <Badge variant="secondary">{String(getValue() ?? "?")}</Badge>,
  },
  {
    accessorKey: "price",
    header: () => <div className="text-right">Preço</div>,
    cell: ({ getValue }) => (
      <div className="tnum text-right whitespace-nowrap">
        {brl(getValue() as number | null)}
      </div>
    ),
  },
  {
    accessorKey: "score",
    header: () => <div className="text-right">Score</div>,
    cell: ({ getValue }) => (
      <div className="tnum text-right">{(getValue() as number | null) ?? "—"}</div>
    ),
  },
  {
    accessorKey: "coupon",
    header: "Cupom",
    cell: ({ getValue }) =>
      getValue() ? (
        <code className="text-xs">{String(getValue())}</code>
      ) : (
        <span style={{ color: "var(--viz-muted)" }}>—</span>
      ),
  },
  {
    accessorKey: "posted_at",
    header: "Quando",
    cell: ({ getValue }) => (
      <span className="tnum whitespace-nowrap" style={{ color: "var(--ink-2)" }}>
        {new Date(String(getValue())).toLocaleString("pt-BR", {
          day: "2-digit",
          month: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
        })}
      </span>
    ),
  },
];

export default function DealsDataTable({
  rows,
  total,
  page,
  pageSize,
}: {
  rows: DealRow[];
  total: number;
  page: number;
  pageSize: number;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const pageCount = Math.max(1, Math.ceil(total / pageSize));

  const goTo = useCallback(
    (p: number) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set("page", String(p));
      router.push(`/deals?${params.toString()}`);
    },
    [router, searchParams],
  );

  const table = useReactTable({
    data: rows,
    columns,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
    pageCount,
  });

  return (
    <div className="space-y-3">
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((hg) => (
            <TableRow key={hg.id}>
              {hg.headers.map((h) => (
                <TableHead key={h.id}>
                  {flexRender(h.column.columnDef.header, h.getContext())}
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {table.getRowModel().rows.length ? (
            table.getRowModel().rows.map((row) => (
              <TableRow key={row.id}>
                {row.getVisibleCells().map((cell) => (
                  <TableCell key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))
          ) : (
            <TableRow>
              <TableCell colSpan={columns.length} className="h-24 text-center">
                Nenhuma oferta encontrada.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      <div className="flex items-center justify-between px-1">
        <p className="text-sm" style={{ color: "var(--viz-muted)" }}>
          {total} ofertas · página {page} de {pageCount}
        </p>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => goTo(page - 1)}
            disabled={page <= 1}
          >
            Anterior
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => goTo(page + 1)}
            disabled={page >= pageCount}
          >
            Próxima
          </Button>
        </div>
      </div>
    </div>
  );
}
