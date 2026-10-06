import { CaseShell } from "./case-shell";

export default async function CaseLayout({ children, params }: LayoutProps<"/cases/[id]">) {
  const { id } = await params;
  // key: switching cases starts from a clean state instead of showing the previous case.
  return (
    <CaseShell key={id} id={id}>
      {children}
    </CaseShell>
  );
}
