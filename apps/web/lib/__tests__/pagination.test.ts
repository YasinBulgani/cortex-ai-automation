/** @jest-environment jsdom */
import { renderHook, act } from "@testing-library/react";
import { usePagination } from "../usePagination";

const makeData = (n: number) => Array.from({ length: n }, (_, i) => i + 1);

describe("usePagination", () => {
  it("starts on page 1 by default", () => {
    const { result } = renderHook(() => usePagination(makeData(50)));
    expect(result.current.page).toBe(1);
  });

  it("returns default pageSize of 20", () => {
    const { result } = renderHook(() => usePagination(makeData(50)));
    expect(result.current.pageSize).toBe(20);
  });

  it("calculates totalPages correctly", () => {
    const { result } = renderHook(() => usePagination(makeData(50)));
    expect(result.current.totalPages).toBe(3);
  });

  it("paginated returns first page slice", () => {
    const { result } = renderHook(() => usePagination(makeData(50)));
    expect(result.current.paginated).toHaveLength(20);
    expect(result.current.paginated[0]).toBe(1);
    expect(result.current.paginated[19]).toBe(20);
  });

  it("next() advances to page 2", () => {
    const { result } = renderHook(() => usePagination(makeData(50)));
    act(() => result.current.next());
    expect(result.current.page).toBe(2);
    expect(result.current.paginated[0]).toBe(21);
  });

  it("prev() does not go below page 1", () => {
    const { result } = renderHook(() => usePagination(makeData(50)));
    act(() => result.current.prev());
    expect(result.current.page).toBe(1);
  });

  it("last() goes to last page", () => {
    const { result } = renderHook(() => usePagination(makeData(50)));
    act(() => result.current.last());
    expect(result.current.page).toBe(3);
    expect(result.current.paginated).toHaveLength(10); // last page has 10 items
  });

  it("first() returns to page 1 after navigating", () => {
    const { result } = renderHook(() => usePagination(makeData(50)));
    act(() => result.current.last());
    act(() => result.current.first());
    expect(result.current.page).toBe(1);
  });

  it("setPage() jumps to arbitrary page", () => {
    const { result } = renderHook(() => usePagination(makeData(50)));
    act(() => result.current.setPage(2));
    expect(result.current.page).toBe(2);
  });

  it("setPage() clamps to totalPages", () => {
    const { result } = renderHook(() => usePagination(makeData(50)));
    act(() => result.current.setPage(999));
    expect(result.current.page).toBe(3);
  });

  it("setPage(0) clamps to 1", () => {
    const { result } = renderHook(() => usePagination(makeData(50)));
    act(() => result.current.setPage(0));
    expect(result.current.page).toBe(1);
  });

  it("hasNext is true on page 1", () => {
    const { result } = renderHook(() => usePagination(makeData(50)));
    expect(result.current.hasNext).toBe(true);
  });

  it("hasNext is false on last page", () => {
    const { result } = renderHook(() => usePagination(makeData(50)));
    act(() => result.current.last());
    expect(result.current.hasNext).toBe(false);
  });

  it("hasPrev is false on page 1", () => {
    const { result } = renderHook(() => usePagination(makeData(50)));
    expect(result.current.hasPrev).toBe(false);
  });

  it("hasPrev is true after next()", () => {
    const { result } = renderHook(() => usePagination(makeData(50)));
    act(() => result.current.next());
    expect(result.current.hasPrev).toBe(true);
  });

  it("empty data → 1 total page, 0 items", () => {
    const { result } = renderHook(() => usePagination([]));
    expect(result.current.totalPages).toBe(1);
    expect(result.current.paginated).toHaveLength(0);
  });

  it("custom pageSize respected", () => {
    const { result } = renderHook(() => usePagination(makeData(10), { pageSize: 3 }));
    expect(result.current.totalPages).toBe(4);
    expect(result.current.paginated).toHaveLength(3);
  });

  it("custom initialPage respected", () => {
    const { result } = renderHook(() => usePagination(makeData(50), { initialPage: 2 }));
    expect(result.current.page).toBe(2);
  });
});
