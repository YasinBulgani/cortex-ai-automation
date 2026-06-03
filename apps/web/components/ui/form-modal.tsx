"use client";

import React from "react";
import { Modal, ModalContent, ModalHeader, ModalTitle, ModalFooter, ModalClose } from "@/components/ui/modal";

interface FormModalProps {
  title: string;
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (e: React.FormEvent) => Promise<void> | void;
  isPending?: boolean;
  submitLabel?: string;
  cancelLabel?: string;
  /** Maksimum genişlik — Tailwind sınıfı, ör. "max-w-md" */
  maxWidth?: string;
  children: React.ReactNode;
}

/**
 * Management sayfalarındaki form + modal kalıbını standartlaştırır.
 * Altında Radix Dialog (Modal) kullanır — erişilebilirlik hazır.
 *
 * Kullanım:
 *   <FormModal
 *     title="Yeni Run"
 *     isOpen={showModal}
 *     onClose={() => setShowModal(false)}
 *     onSubmit={handleCreate}
 *     isPending={createRun.isPending}
 *     submitLabel="Oluştur"
 *   >
 *     <Input name="name" label="Run Adı" />
 *     ...
 *   </FormModal>
 */
export function FormModal({
  title,
  isOpen,
  onClose,
  onSubmit,
  isPending = false,
  submitLabel = "Kaydet",
  cancelLabel = "İptal",
  maxWidth = "max-w-md",
  children,
}: FormModalProps) {
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    void onSubmit(e);
  };

  return (
    <Modal open={isOpen} onOpenChange={(open) => { if (!open) onClose(); }}>
      <ModalContent className={`w-full ${maxWidth}`}>
        <ModalHeader>
          <ModalTitle>{title}</ModalTitle>
        </ModalHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {children}

          <ModalFooter>
            <ModalClose asChild>
              <button
                type="button"
                onClick={onClose}
                className="rounded-md border border-border px-4 py-2 text-[11px] font-medium text-fg-muted transition-colors hover:bg-surface-overlay hover:text-fg"
              >
                {cancelLabel}
              </button>
            </ModalClose>
            <button
              type="submit"
              disabled={isPending}
              className="rounded-md bg-brand px-4 py-2 text-[11px] font-semibold text-brand-fg transition-colors hover:brightness-105 disabled:opacity-40"
            >
              {isPending ? "…" : submitLabel}
            </button>
          </ModalFooter>
        </form>
      </ModalContent>
    </Modal>
  );
}
