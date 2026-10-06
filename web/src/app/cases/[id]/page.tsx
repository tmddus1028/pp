import { redirect } from "next/navigation";

export default async function CasePage({ params }: PageProps<"/cases/[id]">) {
  redirect(`/cases/${(await params).id}/review`);
}
